import os
import subprocess
import requests
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple

# Configuración de formato de commit
COMMIT_FORMAT_CONFIG = {
    "format_rules": """
    Aprovechar, Resumen breve (50 caracteres o menos)
    
    Texto explicativo más detallado, si es necesario. Envuélvalo a unos 72 caracteres más o menos. 
    En algunos contextos, la primera línea se trata como asunto de un correo electrónico y el resto 
    del texto como cuerpo. El espacio en blanco línea que separa el resumen del cuerpo es fundamental 
    (a menos que omita todo el cuerpo); herramientas como rebase pueden confundirse si ejecuta los dos juntos.
    
    Escriba su mensaje de confirmación en imperativo: "Corregir error" y no "Corregido error" o "Corrige error". 
    Esta convención coincide con los mensajes de confirmación generados mediante comandos como git merge y git revert.
    
    Los párrafos adicionales vienen después de las líneas en blanco.
    
    - Las viñetas también están bien
    - Normalmente se utiliza un guión o asterisco para la viñeta, seguido de un espacio único, con líneas en blanco en el medio
    - Usar una sangría colgante
    
    Si utiliza un rastreador de problemas, agregue una referencia a ellos en la parte inferior, como tal:
    
    Soluciona: #123
    """,
    
    "commit_types_rules": """
    Especifica el tipo de commit:
    feat: La nueva característica que agregas a una aplicación en particular
    fix: Un parche para un error
    style: Características o actualizaciones relacionadas con estilos
    refactor: Refactorizar una sección específica de la base de código
    test: Todo lo relacionado con pruebas
    docs: Todo lo relacionado con documentación
    chore: Mantenimiento de código regular
    """,
    
    "style_rules": """
    Separa el título del cuerpo del mensaje con una línea en blanco.
    Tu mensaje de commit no debería contener ningún mensaje de espacios en blanco.
    Quita signos de puntuación innecesarios.
    No termines el título con un punto.
    Usa mayúsculas al inicio del título y por cada párrafo del cuerpo del mensaje.
    Usa el modo imperativo en el título.
    Usa el cuerpo del mensaje para explicar cuáles cambios has hecho y por qué los hiciste.
    No asumas que las personas que revisará el código entiende cuál era el problema original, asegúrate de agregar la información necesaria.
    No piense que tu código se explica solo.
    Sigue la convención del mensaje de commit definida por tu equipo.
    """
}

# Lista de tipos de commit según el estándar
COMMIT_TYPES = [
    {"value": "feat", "name": "feat:     A new feature"},
    {"value": "fix", "name": "fix:      A bug fix"},
    {"value": "docs", "name": "docs:     Documentation only changes"},
    {"value": "style", "name": "style:    Changes that do not affect the meaning of the code"},
    {"value": "refactor", "name": "refactor: A code change that neither fixes a bug nor adds a feature"},
    {"value": "perf", "name": "perf:     A code change that improves performance"},
    {"value": "test", "name": "test:     Adding missing tests or correcting existing tests"},
    {"value": "build", "name": "build:    Changes that affect the build system or external dependencies"},
    {"value": "ci", "name": "ci:       Changes to CI configuration files and scripts"},
    {"value": "chore", "name": "chore:    Other changes that don't modify src or test files"}
]

# Mensajes para el flujo de trabajo
COMMIT_MESSAGES = {
    "type": "Select the type of change that you're committing:",
    "scope": "Denote the SCOPE of this change (optional):",
    "customScope": "Denote the SCOPE of this change:",
    "subject": "Write a SHORT, IMPERATIVE tense description of the change (max 100 chars):\n",
    "body": "Provide a LONGER description of the change (optional). Use '|' to break new line:\n",
    "breaking": "List any BREAKING CHANGES (optional):\n",
    "footer": "List any ISSUES CLOSED by this change (optional). E.g.: #31, #34:\n",
    "confirmCommit": "Are you sure you want to proceed with the commit above?"
}

# Mensajes traducidos para el flujo de trabajo en español
COMMIT_MESSAGES_ES = {
    "type": "Selecciona el tipo de cambio que estás confirmando:",
    "scope": "Indica el ÁMBITO de este cambio (opcional):",
    "customScope": "Indica el ÁMBITO de este cambio:",
    "subject": "Escribe una descripción CORTA e IMPERATIVA del cambio (máx 100 caracteres):\n",
    "body": "Proporciona una descripción MÁS LARGA del cambio (opcional). Usa '|' para saltos de línea:\n",
    "breaking": "Lista cualquier CAMBIO DISRUPTIVO (opcional):\n",
    "footer": "Lista cualquier ISSUE CERRADO por este cambio (opcional). Ej.: #31, #34:\n",
    "confirmCommit": "¿Estás seguro de que deseas proceder con el commit anterior?"
}

def get_git_diff():
    """Get the git diff of staged changes."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True,
            text=False,  # Cambiado a False para manejar bytes en lugar de texto
            check=True
        )
        # Decodificar con manejo de errores
        return result.stdout.decode('utf-8', errors='replace').strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        return ""

def generate_commit_message(api_key, diff, lang='es'):
    """Generate a complete commit message using Qwen 2.5 API.
    Returns a dictionary with all commit message components.
    """
    if not diff:
        return {
            "type": "",
            "scope": "",
            "subject": "No changes to commit" if lang == 'es' else "No hay cambios para hacer commit",
            "body": "",
            "breaking": "",
            "footer": ""
        }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Obtener las reglas de formato de commit
    format_rules = COMMIT_FORMAT_CONFIG["format_rules"]
    commit_types_rules = COMMIT_FORMAT_CONFIG["commit_types_rules"]
    style_rules = COMMIT_FORMAT_CONFIG["style_rules"]
    
    if lang == 'es':
        system_prompt = "You are a helpful assistant that generates clear and concise git commit messages following the conventional commit format and specific formatting rules."
        user_prompt = (
            "Generate a complete commit message for the following changes. "  
            "Follow conventional commit format with the structure: <type>(<scope>): <subject>\n\n<body>\n\n<footer>\n\n"  
            "Where:\n"  
            "- <type> is one of: feat, fix, docs, style, refactor, perf, test, build, ci, chore\n"  
            "- <scope> is optional and indicates the section of the codebase\n"  
            "- <subject> is a short description in imperative mood\n"  
            "- <body> is optional and provides more detailed description\n"  
            "- <footer> is optional and contains references to issues or breaking changes\n\n"  
            "IMPORTANT: Return your response in JSON format with the following structure:\n"  
            "{\n"  
            "  \"type\": \"the commit type\",\n"  
            "  \"scope\": \"the commit scope (without parentheses)\",\n"  
            "  \"subject\": \"the commit subject\",\n"  
            "  \"body\": \"the commit body\",\n"  
            "  \"breaking\": \"any breaking changes\",\n"  
            "  \"footer\": \"any footer information\"\n"  
            "}\n\n"  
            f"Follow these specific formatting rules:\n{format_rules}\n\n"  
            f"Commit types guidelines:\n{commit_types_rules}\n\n"  
            f"Style guidelines:\n{style_rules}\n\n"  
            f"Changes:\n{diff}"
        )
    else:  # Spanish
        system_prompt = "Eres un asistente que genera mensajes de commit claros y concisos siguiendo el formato de commit convencional y reglas específicas de formato."
        user_prompt = (
            "Genera un mensaje de commit completo para los siguientes cambios. "  
            "Sigue el formato de commit convencional con la estructura: <tipo>(<ámbito>): <asunto>\n\n<cuerpo>\n\n<pie>\n\n"  
            "Donde:\n"  
            "- <tipo> es uno de: feat, fix, docs, style, refactor, perf, test, build, ci, chore\n"  
            "- <ámbito> es opcional e indica la sección del código\n"  
            "- <asunto> es una descripción corta en modo imperativo\n"  
            "- <cuerpo> es opcional y proporciona una descripción más detallada\n"  
            "- <pie> es opcional y contiene referencias a issues o cambios disruptivos\n\n"  
            "IMPORTANTE: Devuelve tu respuesta en formato JSON con la siguiente estructura:\n"  
            "{\n"  
            "  \"type\": \"el tipo de commit\",\n"  
            "  \"scope\": \"el ámbito del commit (sin paréntesis)\",\n"  
            "  \"subject\": \"el asunto del commit\",\n"  
            "  \"body\": \"el cuerpo del commit\",\n"  
            "  \"breaking\": \"cualquier cambio disruptivo\",\n"  
            "  \"footer\": \"cualquier información de pie\"\n"  
            "}\n\n"  
            f"Sigue estas reglas específicas de formato:\n{format_rules}\n\n"  
            f"Guía de tipos de commit:\n{commit_types_rules}\n\n"  
            f"Guía de estilo:\n{style_rules}\n\n"  
            f"Cambios:\n{diff}"
        )
    
    data = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 500,  # Aumentado para permitir mensajes más completos
        "temperature": 0.7,
        "stop": ["<|im_end|>"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        ai_response = response.json()["choices"][0]["message"]["content"].strip('"\'\'').strip()
        
        # Intentar parsear la respuesta como JSON
        import json
        try:
            # Extraer solo la parte JSON de la respuesta
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}')
            if json_start >= 0 and json_end >= 0:
                json_str = ai_response[json_start:json_end+1]
                commit_data = json.loads(json_str)
                
                # Asegurarse de que todos los campos existan
                commit_data.setdefault("type", "")
                commit_data.setdefault("scope", "")
                commit_data.setdefault("subject", "")
                commit_data.setdefault("body", "")
                commit_data.setdefault("breaking", "")
                commit_data.setdefault("footer", "")
                
                return commit_data
        except json.JSONDecodeError:
            # Si no se puede parsear como JSON, intentar extraer los componentes manualmente
            pass
            
        # Fallback: extraer manualmente los componentes del mensaje
        lines = ai_response.split('\n')
        header = lines[0] if lines else ""
        
        # Extraer tipo y ámbito del encabezado
        commit_type = ""
        scope = ""
        subject = ""
        
        if ':' in header:
            header_parts = header.split(':', 1)
            type_scope = header_parts[0].strip()
            subject = header_parts[1].strip() if len(header_parts) > 1 else ""
            
            # Extraer tipo y ámbito
            if '(' in type_scope and ')' in type_scope:
                commit_type = type_scope.split('(', 1)[0].strip()
                scope = type_scope.split('(', 1)[1].split(')', 1)[0].strip()
            else:
                commit_type = type_scope
        
        # Extraer cuerpo y pie
        body = ""
        footer = ""
        breaking = ""
        
        if len(lines) > 1:
            # Buscar líneas en blanco para separar cuerpo y pie
            body_start = 1
            while body_start < len(lines) and lines[body_start].strip() == "":
                body_start += 1
                
            footer_start = len(lines)
            for i in range(body_start, len(lines)):
                if lines[i].strip() == "" and i+1 < len(lines) and lines[i+1].strip() != "":
                    footer_start = i+1
                    break
            
            # Extraer cuerpo
            if body_start < footer_start:
                body = "\n".join(lines[body_start:footer_start]).strip()
            
            # Extraer pie y breaking changes
            if footer_start < len(lines):
                footer_text = "\n".join(lines[footer_start:]).strip()
                
                # Buscar breaking changes en el pie
                if "BREAKING CHANGE:" in footer_text:
                    breaking_parts = footer_text.split("BREAKING CHANGE:", 1)
                    breaking = breaking_parts[1].strip() if len(breaking_parts) > 1 else ""
                    footer = breaking_parts[0].strip()
                else:
                    footer = footer_text
        
        return {
            "type": commit_type,
            "scope": scope,
            "subject": subject,
            "body": body,
            "breaking": breaking,
            "footer": footer
        }
        
    except Exception as e:
        print(f"Error generating commit message: {e}")
        return {
            "type": "",
            "scope": "",
            "subject": "",
            "body": "",
            "breaking": "",
            "footer": ""
        }

def get_commit_type(lang='en'):
    """Get the type of commit based on standards."""
    print("\n" + (COMMIT_MESSAGES["type"] if lang == 'es' else COMMIT_MESSAGES_ES["type"]))
    for i, t in enumerate(COMMIT_TYPES, 1):
        print(f"{i}. {t['name']}")
    
    while True:
        try:
            choice = int(input("\nEnter number / Ingresa el número: ")) - 1
            if 0 <= choice < len(COMMIT_TYPES):
                return COMMIT_TYPES[choice]["value"]
            print("Invalid choice. Please try again." if lang == 'es' else "Opción inválida. Inténtalo de nuevo.")
        except ValueError:
            print("Please enter a valid number." if lang == 'es' else "Por favor, ingresa un número válido.")

def get_language_choice():
    """Set default language to Spanish."""
    return 'es'

def get_commit_scope(lang='en'):
    """Get the scope of the changes."""
    prompt = COMMIT_MESSAGES["scope"] if lang == 'es' else COMMIT_MESSAGES_ES["scope"]
    scope = input(f"\n{prompt} ").strip()
    return f"({scope})" if scope else ""

def get_commit_body(lang='en'):
    """Get the body of the commit message."""
    prompt = COMMIT_MESSAGES["body"] if lang == 'es' else COMMIT_MESSAGES_ES["body"]
    print(f"\n{prompt}")
    body = input().strip()
    # Reemplazar | con saltos de línea
    return body.replace("|", "\n")

def get_commit_breaking(lang='en'):
    """Get breaking changes information."""
    prompt = COMMIT_MESSAGES["breaking"] if lang == 'es' else COMMIT_MESSAGES_ES["breaking"]
    print(f"\n{prompt}")
    breaking = input().strip()
    return f"BREAKING CHANGE: {breaking}" if breaking else ""

def get_commit_footer(lang='en'):
    """Get footer information (issues closed)."""
    prompt = COMMIT_MESSAGES["footer"] if lang == 'es' else COMMIT_MESSAGES_ES["footer"]
    print(f"\n{prompt}")
    footer = input().strip()
    return f"Closes: {footer}" if footer else ""

def format_commit_message(commit_type, scope, subject, body="", breaking="", footer=""):
    """Format the commit message according to conventional commit standards and format rules."""
    # Aplicar reglas de estilo al asunto
    # - Usar modo imperativo
    # - No terminar con punto
    # - Usar mayúscula al inicio
    # - Limitar a 50 caracteres si es posible
    subject = subject.strip()
    if subject and not subject[0].isupper():
        subject = subject[0].upper() + subject[1:]
    if subject and subject.endswith("."):
        subject = subject[:-1]
    
    # Formatear el encabezado: tipo(ámbito): asunto
    header = f"{commit_type}{scope}: {subject}"
    
    # Construir el mensaje completo
    message_parts = [header]
    
    # Agregar cuerpo si existe, formateando según las reglas
    if body:
        message_parts.append("")  # Línea en blanco obligatoria entre título y cuerpo
        
        # Formatear el cuerpo: párrafos separados por líneas en blanco
        # y ajustados a 72 caracteres aproximadamente
        formatted_body = []
        paragraphs = body.split("\n\n")
        
        for paragraph in paragraphs:
            # Si es una lista con viñetas, preservar el formato
            if paragraph.strip().startswith("-") or paragraph.strip().startswith("*"):
                formatted_body.append(paragraph)
            else:
                # Formatear párrafo normal
                formatted_body.append(paragraph)
        
        message_parts.append("\n\n".join(formatted_body))
    
    # Agregar breaking changes si existen
    if breaking:
        if not body:  # Si no hay cuerpo, agregar línea en blanco después del encabezado
            message_parts.append("")
        message_parts.append(f"BREAKING CHANGE: {breaking}")
    
    # Agregar footer si existe
    if footer:
        if not body and not breaking:  # Si no hay cuerpo ni breaking changes, agregar línea en blanco
            message_parts.append("")
        
        # Formatear el footer según las reglas
        if not footer.startswith("Soluciona:") and not footer.startswith("Closes:"):
            footer = f"Soluciona: {footer}"
        
        message_parts.append(footer)
    
    return "\n".join(message_parts)

def get_commit_by_id(commit_id, lang='en'):
    """Get commit information by its ID."""
    try:
        # Verificar que el commit existe
        result = subprocess.run(
            ["git", "rev-parse", "--verify", commit_id],
            capture_output=True, text=False, check=True
        )
        
        # Obtener el mensaje del commit
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_id],
            capture_output=True, text=False, check=True
        )
        commit_message = result.stdout.decode('utf-8', errors='replace').strip()
        
        # Obtener el diff del commit
        try:
            diff_result = subprocess.run(
                ["git", "show", commit_id, "--name-status", "--pretty=format:"],
                capture_output=True, text=False, check=True
            )
            diff = diff_result.stdout.decode('utf-8', errors='replace')
        except subprocess.CalledProcessError:
            # Intentar con otro enfoque si el anterior falla
            parent_result = subprocess.run(
                ["git", "rev-parse", f"{commit_id}^"],
                capture_output=True, text=False, check=True
            )
            parent_commit = parent_result.stdout.decode('utf-8', errors='replace').strip()
            
            diff_result = subprocess.run(
                ["git", "diff", parent_commit, commit_id],
                capture_output=True, text=False, check=True
            )
            diff = diff_result.stdout.decode('utf-8', errors='replace')
        
        return {
            "id": commit_id,
            "message": commit_message,
            "diff": diff
        }
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print(f"Commit with ID {commit_id} not found." if lang == 'es' else f"No se encontró el commit con ID {commit_id}.")
        return None

def edit_commit_manually(commit_id, lang='en'):
    """Edit a commit message manually."""
    try:
        # Obtener el mensaje actual del commit
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B", commit_id],
            capture_output=True, text=False, check=True
        )
        old_message = result.stdout.decode('utf-8', errors='replace').strip()
        
        print("\n" + "="*50)
        print(f"Current commit message ({commit_id}):" if lang == 'es' else f"Mensaje actual del commit ({commit_id}):")
        print("-" * 50)
        print(old_message)
        print("="*50)
        
        # Editar manualmente
        print("\nEnter your new commit message (press Enter twice to finish):" if lang == 'es' 
              else "\nIngresa el nuevo mensaje de commit (presiona Enter dos veces para terminar):")
        lines = []
        while True:
            line = input()
            if not line and (not lines or not lines[-1]):
                break
            lines.append(line)
        
        new_message = "\n".join(lines)
        
        if not new_message.strip():
            print("Empty message. Operation cancelled." if lang == 'es' else "Mensaje vacío. Operación cancelada.")
            return
        
        print("\n" + "="*50)
        print("New commit message:" if lang == 'es' else "Nuevo mensaje de commit:")
        print("-" * 50)
        print(new_message)
        print("="*50)
        
        # Confirmar cambio
        confirm = input("\nApply this change? (y/n): " if lang == 'es' 
                     else "¿Aplicar este cambio? (s/n): ").strip().lower()
        
        if confirm in ['y', 's']:
            # Si es el último commit, usar --amend
            head_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=False, check=True
            )
            head_commit = head_result.stdout.decode('utf-8', errors='replace').strip()
            
            if commit_id == head_commit or commit_id.startswith(head_commit) or head_commit.startswith(commit_id):
                subprocess.run(
                    ["git", "commit", "--amend", "-m", new_message],
                    check=True
                )
            else:
                # Para commits anteriores, usar rebase interactivo
                # Crear un script temporal para automatizar el rebase
                script_content = f"#!/bin/sh\nsed -i '1s/pick/edit/' $1\n"
                script_path = Path(__file__).parent / "git_rebase_script.sh"
                
                with open(script_path, "w") as f:
                    f.write(script_content)
                
                # Hacer el script ejecutable
                os.chmod(script_path, 0o755)
                
                # Iniciar rebase interactivo
                parent_commit = subprocess.run(
                    ["git", "rev-parse", f"{commit_id}^"],
                    capture_output=True, text=True, check=True
                ).stdout.strip()
                
                print("Starting interactive rebase..." if lang == 'es' else "Iniciando rebase interactivo...")
                subprocess.run(
                    ["git", "rebase", "-i", "--exec", f"git commit --amend -m '{new_message}' && git rebase --continue", parent_commit],
                    check=True
                )
                
                # Eliminar el script temporal
                if script_path.exists():
                    os.remove(script_path)
            
            print("\n✅ Commit message updated successfully!" if lang == 'es' 
                  else "\n✅ ¡Mensaje de commit actualizado correctamente!")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("Operation failed. Make sure the commit exists and you have permission to modify it." if lang == 'es'
              else "La operación falló. Asegúrate de que el commit existe y tienes permisos para modificarlo.")

def rename_last_commit(api_key, lang='en'):
    """Rename the last commit if it hasn't been pushed yet."""
    try:
        # Check if there are any commits to rename
        subprocess.run(["git", "log", "-1"], check=True, capture_output=True, text=False)
        
        # Get the current commit message
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=%B"],
            capture_output=True, text=False, check=True
        )
        old_message = result.stdout.decode('utf-8', errors='replace').strip()
        
        print("\n" + "="*50)
        print("Last commit message:" if lang == 'es' else "Último mensaje de commit:")
        print("-" * 50)
        print(old_message)
        print("="*50)
        
        # Opciones para editar
        print("\nOptions / Opciones:")
        print("(A) AI-assisted edit / Edición asistida por IA")
        print("(M) Manual edit / Edición manual")
        print("(C) Cancel / Cancelar")
        
        edit_choice = input("\nEnter your choice / Ingresa tu opción: ").strip().upper()
        
        if edit_choice == 'C':
            print("Operation cancelled." if lang == 'es' else "Operación cancelada.")
            return
        
        if edit_choice == 'M':
            # Obtener el ID del último commit
            head_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=False, check=True
            )
            head_commit = head_result.stdout.decode('utf-8', errors='replace').strip()
            
            # Editar manualmente
            edit_commit_manually(head_commit, lang)
            return
        
        # Generate new message with AI
        print("\nGenerating new commit message..." if lang == 'es' else "\nGenerando nuevo mensaje de commit...")
        
        # Get the diff of the last commit
        try:
            diff = subprocess.run(
                ["git", "show", "HEAD", "--name-status", "--pretty=format:"],
                capture_output=True, text=True, check=True
            ).stdout
        except subprocess.CalledProcessError:
            # Intentar con otro enfoque si el anterior falla
            diff = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD"],
                capture_output=True, text=True, check=True
            ).stdout
        
        # Generate message with AI
        commit_data = generate_commit_message(api_key, diff, lang)
        
        if not commit_data or not commit_data.get("subject"):
            print("Failed to generate commit message" if lang == 'es' 
                  else "Error al generar el mensaje de commit")
            return
        
        # Permitir al usuario editar cada campo
        print("\n" + "-" * 50)
        print("\nEditing commit message / Editando mensaje de commit:")
        
        if lang == 'es':
            new_type = input(f"\nCommit TYPE [{commit_data['type']}]: ").strip() or commit_data['type']
            new_scope = input(f"\nCommit SCOPE [{commit_data['scope']}]: ").strip() or commit_data['scope']
            new_subject = input(f"\nCommit SUBJECT [{commit_data['subject']}]: ").strip() or commit_data['subject']
            new_body = input(f"\nCommit BODY (use '|' for line breaks)\n[{commit_data['body'].replace('\n', '|')}]: ").strip()
            new_body = new_body.replace('|', '\n') if new_body else commit_data['body']
            new_breaking = input(f"\nBREAKING CHANGES [{commit_data['breaking']}]: ").strip() or commit_data['breaking']
            new_footer = input(f"\nFOOTER [{commit_data['footer']}]: ").strip() or commit_data['footer']
        else:
            new_type = input(f"\nTIPO de commit [{commit_data['type']}]: ").strip() or commit_data['type']
            new_scope = input(f"\nÁMBITO del commit [{commit_data['scope']}]: ").strip() or commit_data['scope']
            new_subject = input(f"\nASUNTO del commit [{commit_data['subject']}]: ").strip() or commit_data['subject']
            new_body = input(f"\nCUERPO del commit (usa '|' para saltos de línea)\n[{commit_data['body'].replace('\n', '|')}]: ").strip()
            new_body = new_body.replace('|', '\n') if new_body else commit_data['body']
            new_breaking = input(f"\nCAMBIOS DISRUPTIVOS [{commit_data['breaking']}]: ").strip() or commit_data['breaking']
            new_footer = input(f"\nPIE DE PÁGINA [{commit_data['footer']}]: ").strip() or commit_data['footer']
        
        # Formatear el encabezado: tipo(ámbito): asunto
        header = new_type
        if new_scope:
            header += f"({new_scope})"
        header += f": {new_subject}"
        
        # Formatear mensaje completo
        formatted_message = header
        if new_body:
            formatted_message += "\n\n" + new_body
        if new_breaking:
            formatted_message += "\n\nBREAKING CHANGE: " + new_breaking
        if new_footer:
            formatted_message += "\n\n" + new_footer
        
        print("\n" + "="*50)
        print("New commit message:" if lang == 'es' else "Nuevo mensaje de commit:")
        print("-" * 50)
        print(formatted_message)
        print("="*50)
        
        # Ask for confirmation
        confirm = input("\nApply this change? (y/n): " if lang == 'es' 
                     else "¿Aplicar este cambio? (s/n): ").strip().lower()
        
        if confirm in ['y', 's']:
            subprocess.run(
                ["git", "commit", "--amend", "-m", formatted_message],
                check=True
            )
            print("\n✅ Commit message updated successfully!" if lang == 'es' 
                  else "\n✅ ¡Mensaje de commit actualizado correctamente!")
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("Make sure you have at least one commit to rename." if lang == 'es'
              else "Asegúrate de tener al menos un commit para renombrar.")

def create_new_commit(api_key, lang='en'):
    """Create a new commit with AI-generated message and additional options."""
    # Primero añadir todos los cambios al staging
    stage_changes(all_files=True, lang=lang)
    
    # Get git diff
    diff = get_git_diff()
    if not diff:
        print("No changes to commit" if lang == 'es' else "No hay cambios para hacer commit")
        return
    
    # Historial de mensajes generados
    message_history = []
    current_index = -1
    
    while True:
        # Generate commit message
        print("Generating commit message..." if lang == 'es' else "Generando mensaje de commit...")
        commit_data = generate_commit_message(api_key, diff, lang)
        
        if not commit_data or not commit_data.get("subject"):
            print("Failed to generate commit message" if lang == 'es' else "Error al generar el mensaje de commit")
            return
        
        # Si es la primera generación, mantener los campos generados por la IA
        if current_index < 0:
            # Guardar en el historial
            message_history.append(commit_data)
            current_index = 0
        else:
            # Si estamos regenerando, reemplazar todos los mensajes siguientes
            if current_index < len(message_history) - 1:
                message_history = message_history[:current_index + 1]
            
            message_history.append(commit_data)
            current_index = len(message_history) - 1
        
        # Formatear el mensaje para mostrarlo
        current_data = message_history[current_index]
        
        # Mostrar el mensaje formateado
        print("\n" + "="*50)
        print("Commit message:" if lang == 'es' else "Mensaje de commit:")
        print("-" * 50)
        
        # Formatear el encabezado: tipo(ámbito): asunto
        header = current_data["type"]
        if current_data["scope"]:
            header += f"({current_data['scope']})" 
        header += f": {current_data['subject']}"
        
        print(header)
        
        if current_data["body"]:
            print("\n" + current_data["body"])
        
        footer_text = ""
        if current_data["breaking"]:
            footer_text += f"\n\nBREAKING CHANGE: {current_data['breaking']}"
        
        if current_data["footer"]:
            footer_text += f"\n\n{current_data['footer']}"
        
        if footer_text:
            print(footer_text)
        
        print("\n" + "="*50)
        
        # Formatear el mensaje completo para el commit
        formatted_message = header
        if current_data["body"]:
            formatted_message += "\n\n" + current_data["body"]
        if current_data["breaking"]:
            formatted_message += "\n\nBREAKING CHANGE: " + current_data["breaking"]
        if current_data["footer"]:
            formatted_message += "\n\n" + current_data["footer"]
        
        # Mostrar opciones
        print("\nOptions / Opciones:")
        print("(A) Accept and commit / Aceptar y hacer commit")
        print("(R) Regenerate message / Regenerar mensaje")
        print("(P) Previous message / Mensaje anterior" if current_index > 0 else "")
        print("(N) Next message / Mensaje siguiente" if current_index < len(message_history) - 1 else "")
        print("(E) Edit manually / Editar manualmente")
        print("(C) Cancel / Cancelar")
        
        choice = input("\nEnter your choice / Ingresa tu opción: ").strip().upper()
        
        if choice == 'A':  # Aceptar y hacer commit
            try:
                subprocess.run(["git", "commit", "-m", formatted_message], check=True)
                print("\n✅ Commit created successfully!" if lang == 'es' else "\n✅ ¡Commit creado exitosamente!")
                break
            except subprocess.CalledProcessError as e:
                print(f"Error creating commit: {e}" if lang == 'es' else f"Error al crear el commit: {e}")
                break
        
        elif choice == 'R':  # Regenerar mensaje
            continue  # Volver al inicio del bucle para generar un nuevo mensaje
        
        elif choice == 'P' and current_index > 0:  # Mensaje anterior
            current_index -= 1
            formatted_message = message_history[current_index]["formatted"]
        
        elif choice == 'N' and current_index < len(message_history) - 1:  # Mensaje siguiente
            current_index += 1
            formatted_message = message_history[current_index]["formatted"]
        
        elif choice == 'E':  # Editar manualmente
            # Obtener los datos actuales para edición
            current_data = message_history[current_index]
            
            # Permitir al usuario editar cada campo
            print("\n" + "-" * 50)
            print("\nEditing commit message / Editando mensaje de commit:")
            
            if lang == 'es':
                new_type = input(f"\nCommit TYPE [{current_data['type']}]: ").strip() or current_data['type']
                new_scope = input(f"\nCommit SCOPE [{current_data['scope']}]: ").strip() or current_data['scope']
                new_subject = input(f"\nCommit SUBJECT [{current_data['subject']}]: ").strip() or current_data['subject']
                new_body = input(f"\nCommit BODY (use '|' for line breaks)\n[{current_data['body'].replace('\n', '|')}]: ").strip()
                new_body = new_body.replace('|', '\n') if new_body else current_data['body']
                new_breaking = input(f"\nBREAKING CHANGES [{current_data['breaking']}]: ").strip() or current_data['breaking']
                new_footer = input(f"\nFOOTER [{current_data['footer']}]: ").strip() or current_data['footer']
            else:
                new_type = input(f"\nTIPO de commit [{current_data['type']}]: ").strip() or current_data['type']
                new_scope = input(f"\nÁMBITO del commit [{current_data['scope']}]: ").strip() or current_data['scope']
                new_subject = input(f"\nASUNTO del commit [{current_data['subject']}]: ").strip() or current_data['subject']
                new_body = input(f"\nCUERPO del commit (usa '|' para saltos de línea)\n[{current_data['body'].replace('\n', '|')}]: ").strip()
                new_body = new_body.replace('|', '\n') if new_body else current_data['body']
                new_breaking = input(f"\nCAMBIOS DISRUPTIVOS [{current_data['breaking']}]: ").strip() or current_data['breaking']
                new_footer = input(f"\nPIE DE PÁGINA [{current_data['footer']}]: ").strip() or current_data['footer']
            
            # Crear un nuevo objeto de datos de commit con los valores editados
            edited_data = {
                "type": new_type,
                "scope": new_scope,
                "subject": new_subject,
                "body": new_body,
                "breaking": new_breaking,
                "footer": new_footer
            }
            
            # Añadir al historial
            if current_index < len(message_history) - 1:
                message_history = message_history[:current_index + 1]
            
            message_history.append(edited_data)
            current_index = len(message_history) - 1
        
        elif choice == 'C':  # Cancelar
            print("Commit cancelled." if lang == 'es' else "Commit cancelado.")
            break
        
        else:
            print("Invalid option. Please try again." if lang == 'es' else "Opción inválida. Inténtalo de nuevo.")

def edit_specific_commit(api_key, lang='en'):
    """Edit a specific commit by its ID."""
    # Mostrar los últimos commits para referencia
    print("\nShowing last 10 commits for reference:" if lang == 'es' else "\nMostrando los últimos 10 commits como referencia:")
    subprocess.run(
        ["git", "log", "--oneline", "-n", "10"],
        check=True
    )
    
    # Solicitar ID del commit
    commit_id = input("\nEnter commit ID / Ingresa el ID del commit: ").strip()
    
    if not commit_id:
        print("Operation cancelled." if lang == 'es' else "Operación cancelada.")
        return
    
    # Obtener información del commit
    commit_info = get_commit_by_id(commit_id, lang)
    
    if not commit_info:
        return
    
    # Opciones para editar
    print("\nOptions / Opciones:")
    print("(A) AI-assisted edit / Edición asistida por IA")
    print("(M) Manual edit / Edición manual")
    print("(C) Cancel / Cancelar")
    
    edit_choice = input("\nEnter your choice / Ingresa tu opción: ").strip().upper()
    
    if edit_choice == 'C':
        print("Operation cancelled." if lang == 'es' else "Operación cancelada.")
        return
    
    if edit_choice == 'M':
        # Editar manualmente
        edit_commit_manually(commit_id, lang)
        return
    
    # Edición asistida por IA
    # Generate message with AI
    print("\nGenerating new commit message..." if lang == 'es' else "\nGenerando nuevo mensaje de commit...")
    commit_data = generate_commit_message(api_key, commit_info["diff"], lang)
    
    if not commit_data or not commit_data.get("subject"):
        print("Failed to generate commit message" if lang == 'es' 
              else "Error al generar el mensaje de commit")
        return
    
    # Permitir al usuario editar cada campo
    print("\n" + "-" * 50)
    print("\nEditing commit message / Editando mensaje de commit:")
    
    if lang == 'es':
        new_type = input(f"\nCommit TYPE [{commit_data['type']}]: ").strip() or commit_data['type']
        new_scope = input(f"\nCommit SCOPE [{commit_data['scope']}]: ").strip() or commit_data['scope']
        new_subject = input(f"\nCommit SUBJECT [{commit_data['subject']}]: ").strip() or commit_data['subject']
        new_body = input(f"\nCommit BODY (use '|' for line breaks)\n[{commit_data['body'].replace('\n', '|')}]: ").strip()
        new_body = new_body.replace('|', '\n') if new_body else commit_data['body']
        new_breaking = input(f"\nBREAKING CHANGES [{commit_data['breaking']}]: ").strip() or commit_data['breaking']
        new_footer = input(f"\nFOOTER [{commit_data['footer']}]: ").strip() or commit_data['footer']
    else:
        new_type = input(f"\nTIPO de commit [{commit_data['type']}]: ").strip() or commit_data['type']
        new_scope = input(f"\nÁMBITO del commit [{commit_data['scope']}]: ").strip() or commit_data['scope']
        new_subject = input(f"\nASUNTO del commit [{commit_data['subject']}]: ").strip() or commit_data['subject']
        new_body = input(f"\nCUERPO del commit (usa '|' para saltos de línea)\n[{commit_data['body'].replace('\n', '|')}]: ").strip()
        new_body = new_body.replace('|', '\n') if new_body else commit_data['body']
        new_breaking = input(f"\nCAMBIOS DISRUPTIVOS [{commit_data['breaking']}]: ").strip() or commit_data['breaking']
        new_footer = input(f"\nPIE DE PÁGINA [{commit_data['footer']}]: ").strip() or commit_data['footer']
    
    # Formatear el encabezado: tipo(ámbito): asunto
    header = new_type
    if new_scope:
        header += f"({new_scope})"
    header += f": {new_subject}"
    
    # Formatear mensaje completo
    formatted_message = header
    if new_body:
        formatted_message += "\n\n" + new_body
    if new_breaking:
        formatted_message += "\n\nBREAKING CHANGE: " + new_breaking
    if new_footer:
        formatted_message += "\n\n" + new_footer
    
    print("\n" + "="*50)
    print("New commit message:" if lang == 'es' else "Nuevo mensaje de commit:")
    print("-" * 50)
    print(formatted_message)
    print("="*50)
    
    # Ask for confirmation
    confirm = input("\nApply this change? (y/n): " if lang == 'es' 
                 else "¿Aplicar este cambio? (s/n): ").strip().lower()
    
    if confirm in ['y', 's']:
        # Si es el último commit, usar --amend
        head_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        if commit_id == head_commit or commit_id.startswith(head_commit) or head_commit.startswith(commit_id):
            subprocess.run(
                ["git", "commit", "--amend", "-m", formatted_message],
                check=True
            )
        else:
            # Para commits anteriores, usar rebase interactivo
            # Crear un script temporal para automatizar el rebase
            script_content = f"#!/bin/sh\nsed -i '1s/pick/edit/' $1\n"
            script_path = Path(__file__).parent / "git_rebase_script.sh"
            
            with open(script_path, "w") as f:
                f.write(script_content)
            
            # Hacer el script ejecutable
            os.chmod(script_path, 0o755)
            
            # Iniciar rebase interactivo
            parent_result = subprocess.run(
                ["git", "rev-parse", f"{commit_id}^"],
                capture_output=True, text=False, check=True
            )
            parent_commit = parent_result.stdout.decode('utf-8', errors='replace').strip()
            
            print("Starting interactive rebase..." if lang == 'es' else "Iniciando rebase interactivo...")
            subprocess.run(
                ["git", "rebase", "-i", "--exec", f"git commit --amend -m '{formatted_message}' && git rebase --continue", parent_commit],
                check=True
            )
            
            # Eliminar el script temporal
            if script_path.exists():
                os.remove(script_path)
        
        print("\n✅ Commit message updated successfully!" if lang == 'es' 
              else "\n✅ ¡Mensaje de commit actualizado correctamente!")

def main_ai_commit():
    # Load environment variables
    env_path = Path(__file__).parent / '.env'
    if not env_path.exists():
        print("Error: .env file not found. Please create it with your Qwen API key.")
        print("Example .env file content:")
        print("QWEN_API_KEY=your_api_key_here")
        return
        
    load_dotenv(env_path)
    api_key = os.getenv("QWEN_API_KEY")
    
    if not api_key:
        print("Error: QWEN_API_KEY not found in .env file")
        return
    
    # Get language choice
    lang = get_language_choice()
    
    # Ask user what they want to do
    print("\nWhat would you like to do? / ¿Qué te gustaría hacer?")
    print("1. Create a new commit / Crear un nuevo commit")
    print("2. Rename last commit / Renombrar el último commit")
    print("3. Edit specific commit by ID / Editar commit específico por ID")
    
    while True:
        choice = input("\nEnter your choice (1-3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3." if lang == 'es' else "Opción inválida. Por favor, ingresa 1, 2 o 3.")
    
    if choice == '2':
        rename_last_commit(api_key, lang)
    elif choice == '3':
        edit_specific_commit(api_key, lang)
    else:
        create_new_commit(api_key, lang)

def show_status(lang: str = 'en') -> None:
    """Show the current status of the repository."""
    print("\n" + ("=== Repository Status ===" if lang == 'es' else "=== Estado del Repositorio ==="))
    commands = []
    
    # Git status
    commands.append("git status")
    subprocess.run(["git", "status"])
    
    # Show branch information
    commands.append("git branch -v")
    subprocess.run(["git", "branch", "-v"])
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def stage_changes(files: List[str] = None, all_files: bool = False, lang: str = 'en') -> None:
    """Stage changes in the working directory."""
    commands = []
    
    if all_files:
        commands.append("git add .")
        subprocess.run(["git", "add", "."])
        print("\n" + ("All changes staged successfully!" if lang == 'es' 
                       else "¡Todos los cambios añadidos al área de preparación!"))
    elif files:
        for file in files:
            commands.append(f"git add {file}")
            subprocess.run(["git", "add", file])
        print("\n" + (f"Staged {len(files)} files successfully!" if lang == 'es' 
                         else f"¡{len(files)} archivos añadidos al área de preparación!"))
    else:
        print("\n" + ("No files specified to stage. Use --all to stage all changes." 
                       if lang == 'es' else "No se especificaron archivos. Usa --all para añadir todos los cambios."))
        return
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def unstage_changes(files: List[str] = None, all_files: bool = False, lang: str = 'en') -> None:
    """Unstage changes from the staging area."""
    commands = []
    
    if all_files:
        commands.append("git reset")
        subprocess.run(["git", "reset"])
        print("\n" + ("All changes unstaged successfully!" if lang == 'es' 
                       else "¡Todos los cambios eliminados del área de preparación!"))
    elif files:
        for file in files:
            commands.append(f"git restore --staged {file}")
            subprocess.run(["git", "restore", "--staged", file])
        print("\n" + (f"Unstaged {len(files)} files successfully!" if lang == 'es' 
                         else f"¡{len(files)} archivos eliminados del área de preparación!"))
    else:
        print("\n" + ("No files specified to unstage. Use --all to unstage all changes." 
                       if lang == 'es' else "No se especificaron archivos. Usa --all para quitar todos los cambios."))
        return
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def create_branch(branch_name: str, switch: bool = False, lang: str = 'en') -> None:
    """Create a new branch and optionally switch to it."""
    commands = []
    
    if not branch_name:
        print("\n" + ("Branch name is required!" if lang == 'es' else "¡Se requiere un nombre para la rama!"))
        return
    
    if switch:
        commands.append(f"git checkout -b {branch_name}")
        result = subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error creating branch: {result.stderr}" if lang == 'es' 
                           else f"Error al crear la rama: {result.stderr}"))
            return
    else:
        commands.append(f"git branch {branch_name}")
        result = subprocess.run(["git", "branch", branch_name], capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error creating branch: {result.stderr}" if lang == 'es' 
                           else f"Error al crear la rama: {result.stderr}"))
            return
    
    print("\n" + (f"Branch '{branch_name}' created successfully!" if lang == 'es' 
                   else f"¡Rama '{branch_name}' creada con éxito!"))
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def switch_branch(branch_name: str, create: bool = False, lang: str = 'en') -> None:
    """Switch to an existing branch or create and switch to a new one."""
    commands = []
    
    if not branch_name:
        print("\n" + ("Branch name is required!" if lang == 'es' else "¡Se requiere un nombre para la rama!"))
        return
    
    if create:
        commands.append(f"git checkout -b {branch_name}")
        result = subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True, text=True)
    else:
        commands.append(f"git checkout {branch_name}")
        result = subprocess.run(["git", "checkout", branch_name], capture_output=True, text=True)
    
    if result.returncode != 0:
        print("\n" + (f"Error switching branch: {result.stderr}" if lang == 'es' 
                       else f"Error al cambiar de rama: {result.stderr}"))
        return
    
    print("\n" + (f"Switched to branch '{branch_name}'" if lang == 'es' 
                   else f"Cambiado a la rama '{branch_name}'") + " 🎉")
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def list_branches(lang: str = 'en') -> None:
    """List all local and remote branches."""
    commands = ["git branch -a"]
    
    print("\n" + ("=== Local Branches ===" if lang == 'es' else "=== Ramas Locales ==="))
    subprocess.run(["git", "branch"])
    
    print("\n" + ("=== Remote Branches ===" if lang == 'es' else "=== Ramas Remotas ==="))
    subprocess.run(["git", "branch", "-r"])
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def push_changes(remote: str = "origin", branch: str = None, setUpstream: bool = False, lang: str = 'en') -> None:
    """Push changes to a remote repository."""
    commands = []
    
    if not branch:
        # Get current branch name
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + ("Error getting current branch name!" if lang == 'es' 
                          else "¡Error al obtener el nombre de la rama actual!"))
            return
        branch = result.stdout.strip()
    
    if setUpstream:
        commands.append(f"git push -u {remote} {branch}")
        result = subprocess.run(["git", "push", "-u", remote, branch], 
                              capture_output=True, text=True)
    else:
        commands.append(f"git push {remote} {branch}")
        result = subprocess.run(["git", "push", remote, branch], 
                              capture_output=True, text=True)
    
    if result.returncode != 0:
        print("\n" + (f"Error pushing changes: {result.stderr}" if lang == 'es' 
                       else f"Error al subir cambios: {result.stderr}"))
        return
    
    print("\n" + (f"Successfully pushed to {remote}/{branch}" if lang == 'es' 
                   else f"Cambios subidos exitosamente a {remote}/{branch}") + " 🚀")
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def pull_changes(remote: str = "origin", branch: str = None, rebase: bool = False, lang: str = 'en') -> None:
    """Pull changes from a remote repository."""
    commands = []
    
    if not branch:
        # Get current branch name
        result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + ("Error getting current branch name!" if lang == 'es' 
                          else "¡Error al obtener el nombre de la rama actual!"))
            return
        branch = result.stdout.strip()
    
    if rebase:
        commands.append(f"git pull --rebase {remote} {branch}")
        result = subprocess.run(["git", "pull", "--rebase", remote, branch], 
                              capture_output=True, text=True)
    else:
        commands.append(f"git pull {remote} {branch}")
        result = subprocess.run(["git", "pull", remote, branch], 
                              capture_output=True, text=True)
    
    if result.returncode != 0:
        print("\n" + (f"Error pulling changes: {result.stderr}" if lang == 'es' 
                       else f"Error al descargar cambios: {result.stderr}"))
        return
    
    print("\n" + (f"Successfully pulled from {remote}/{branch}" if lang == 'es' 
                   else f"Cambios descargados exitosamente de {remote}/{branch}") + " 🔄")
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def stash_changes(message: str = "", pop: bool = False, apply: bool = False, list_stash: bool = False, lang: str = 'en') -> None:
    """Stash changes in the working directory."""
    commands = []
    
    if list_stash:
        commands.append("git stash list")
        print("\n" + ("=== Stashed Changes ===" if lang == 'es' else "=== Cambios Guardados Temporalmente ==="))
        subprocess.run(["git", "stash", "list"])
        return
    
    if pop:
        commands.append("git stash pop")
        result = subprocess.run(["git", "stash", "pop"], capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error applying stash: {result.stderr}" if lang == 'es' 
                          else f"Error al aplicar los cambios guardados: {result.stderr}"))
            return
        print("\n" + ("Changes applied successfully!" if lang == 'es' 
                         else "¡Cambios aplicados exitosamente!"))
    elif apply:
        commands.append("git stash apply")
        result = subprocess.run(["git", "stash", "apply"], capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error applying stash: {result.stderr}" if lang == 'es' 
                          else f"Error al aplicar los cambios guardados: {result.stderr}"))
            return
        print("\n" + ("Changes applied successfully!" if lang == 'es' 
                         else "¡Cambios aplicados exitosamente!"))
    else:
        stash_cmd = ["git", "stash", "save"]
        if message:
            stash_cmd.append(message)
            commands.append(f"git stash save \"{message}\"")
        else:
            commands.append("git stash save")
        
        result = subprocess.run(stash_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error stashing changes: {result.stderr}" if lang == 'es' 
                          else f"Error al guardar los cambios temporalmente: {result.stderr}"))
            return
        print("\n" + ("Changes stashed successfully!" if lang == 'es' 
                         else "¡Cambios guardados temporalmente!"))
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def undo_last_commit(keep_changes: bool = True, lang: str = 'en') -> None:
    """Undo the last commit, optionally keeping the changes."""
    commands = []
    
    if keep_changes:
        commands.append("git reset --soft HEAD~1")
        result = subprocess.run(["git", "reset", "--soft", "HEAD~1"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error undoing last commit: {result.stderr}" if lang == 'es' 
                          else f"Error al deshacer el último commit: {result.stderr}"))
            return
        print("\n" + ("Last commit undone, changes are now staged!" if lang == 'es' 
                       else "¡Último commit deshecho, los cambios están en el área de preparación!"))
    else:
        commands.append("git reset --hard HEAD~1")
        confirm = input(("\nThis will permanently discard changes in the last commit. Continue? (y/n): " 
                        if lang == 'es' else 
                        "\nEsto descartará permanentemente los cambios del último commit. ¿Continuar? (s/n): "))
        if confirm.lower() not in ['y', 's', 'yes', 'si']:
            print("\n" + ("Operation cancelled." if lang == 'es' else "Operación cancelada."))
            return
        
        result = subprocess.run(["git", "reset", "--hard", "HEAD~1"], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print("\n" + (f"Error undoing last commit: {result.stderr}" if lang == 'es' 
                          else f"Error al deshacer el último commit: {result.stderr}"))
            return
        print("\n" + ("Last commit and changes discarded!" if lang == 'es' 
                       else "¡Último commit y cambios descartados!"))
    
    print("\n" + ("=== Commands executed ===" if lang == 'es' else "=== Comandos ejecutados ==="))
    for cmd in commands:
        print(f"$ {cmd}")

def show_help(lang: str = 'en') -> None:
    """Show help information for the Git helper."""
    help_text = """
Git Helper - Comandos disponibles / Available commands:

1.  Gestión de cambios / Change Management:
    - status: Muestra el estado actual del repositorio / Show repository status
    - stage [archivos...] --all: Añade archivos al área de preparación / Add files to staging area
    - unstage [archivos...] --all: Quita archivos del área de preparación / Remove files from staging area

2.  Sincronización / Synchronization:
    - push [rama] --set-upstream: Envía cambios al repositorio remoto / Push changes to remote repository
    - pull [rama] --rebase: Obtiene cambios del repositorio remoto / Pull changes from remote repository

3.  Gestión de ramas / Branch Management:
    - branch: Lista todas las ramas / List all branches
    - new-branch <nombre> [-s|--switch]: Crea una nueva rama / Create a new branch
    - switch <rama> [-c|--create]: Cambia a una rama existente o crea una nueva / Switch to a branch

4.  Utilidades / Utilities:
    - stash [mensaje] --pop --apply --list: Guarda cambios temporalmente / Stash changes
    - undo-commit [--hard]: Deshace el último commit / Undo last commit
    - help: Muestra esta ayuda / Show this help

Ejemplos / Examples:
  $ python commit_helper.py stage archivo1.txt archivo2.py
  $ python commit_helper.py push --set-upstream
  $ python commit_helper.py new-branch feature/nueva-funcion -s
  $ python commit_helper.py stash "Cambios temporales"
  $ python commit_helper.py undo-commit --hard
"""
    print(help_text)

def parse_arguments():
    """Parse command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Git Helper - Herramienta de ayuda para Git')
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar / Command to execute')
    
    # Status command
    subparsers.add_parser('status', help='Muestra el estado del repositorio / Show repository status')
    
    # Stage command
    stage_parser = subparsers.add_parser('stage', help='Añade archivos al área de preparación / Add files to staging')
    stage_parser.add_argument('files', nargs='*', help='Archivos para añadir / Files to add')
    stage_parser.add_argument('--all', action='store_true', help='Añadir todos los cambios / Add all changes')
    
    # Unstage command
    unstage_parser = subparsers.add_parser('unstage', help='Quita archivos del área de preparación / Unstage files')
    unstage_parser.add_argument('files', nargs='*', help='Archivos para quitar / Files to unstage')
    unstage_parser.add_argument('--all', action='store_true', help='Quitar todos los cambios / Unstage all changes')
    
    # Push command
    push_parser = subparsers.add_parser('push', help='Envía cambios al repositorio remoto / Push changes to remote')
    push_parser.add_argument('branch', nargs='?', help='Rama a la que hacer push / Branch to push to')
    push_parser.add_argument('--set-upstream', '-u', action='store_true', 
                           help='Establece la rama de seguimiento / Set upstream branch')
    
    # Pull command
    pull_parser = subparsers.add_parser('pull', help='Obtiene cambios del repositorio remoto / Pull changes from remote')
    pull_parser.add_argument('branch', nargs='?', help='Rama de la que hacer pull / Branch to pull from')
    pull_parser.add_argument('--rebase', action='store_true', 
                           help='Realiza un rebase al hacer pull / Perform a rebase when pulling')
    
    # Branch command
    branch_parser = subparsers.add_parser('branch', help='Lista todas las ramas / List all branches')
    
    # New branch command
    new_branch_parser = subparsers.add_parser('new-branch', help='Crea una nueva rama / Create a new branch')
    new_branch_parser.add_argument('name', help='Nombre de la nueva rama / New branch name')
    new_branch_parser.add_argument('--switch', '-s', action='store_true', 
                                 help='Cambiar a la nueva rama después de crearla / Switch to the new branch after creating it')
    
    # Switch command
    switch_parser = subparsers.add_parser('switch', help='Cambia a una rama existente / Switch to an existing branch')
    switch_parser.add_argument('branch', help='Nombre de la rama / Branch name')
    switch_parser.add_argument('--create', '-c', action='store_true', 
                             help='Crea la rama si no existe / Create the branch if it does not exist')
    
    # Stash command
    stash_parser = subparsers.add_parser('stash', help='Guarda cambios temporalmente / Stash changes')
    stash_parser.add_argument('message', nargs='?', default='', 
                            help='Mensaje descriptivo / Descriptive message')
    stash_parser.add_argument('--pop', action='store_true', 
                            help='Aplica y elimina el último stash / Apply and remove the latest stash')
    stash_parser.add_argument('--apply', action='store_true', 
                            help='Aplica el último stash sin eliminarlo / Apply the latest stash without removing it')
    stash_parser.add_argument('--list', '-l', action='store_true', 
                            help='Lista los stashes guardados / List saved stashes')
    
    # Undo commit command
    undo_parser = subparsers.add_parser('undo-commit', help='Deshace el último commit / Undo last commit')
    undo_parser.add_argument('--hard', action='store_true', 
                           help='Descarta los cambios del commit / Discard commit changes')
    
    # Help command
    subparsers.add_parser('help', help='Muestra esta ayuda / Show this help')
    
    # Language argument for all commands
    parser.add_argument('--lang', choices=['en', 'es'], default='en',
                      help='Idioma / Language (en/es)')
    
    return parser.parse_args()

def main():
    """Main function to handle command execution."""
    # Check if no arguments were provided, then run the AI commit helper
    if len(sys.argv) == 1:
        main_ai_commit()
        return
        
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set language
        lang = getattr(args, 'lang', 'en')
        
        # Execute the appropriate command
        if args.command == 'status':
            show_status(lang)
            
        elif args.command == 'stage':
            if args.all or not args.files:
                stage_changes(all_files=True, lang=lang)
            elif args.files:
                stage_changes(files=args.files, lang=lang)
                
        elif args.command == 'unstage':
            if args.all or not args.files:
                unstage_changes(all_files=True, lang=lang)
            elif args.files:
                unstage_changes(files=args.files, lang=lang)
                
        elif args.command == 'push':
            push_changes(branch=args.branch, setUpstream=args.set_upstream, lang=lang)
            
        elif args.command == 'pull':
            pull_changes(branch=args.branch, rebase=args.rebase, lang=lang)
            
        elif args.command == 'branch':
            list_branches(lang)
            
        elif args.command == 'new-branch':
            create_branch(args.name, switch=args.switch, lang=lang)
            
        elif args.command == 'switch':
            if args.create:
                create_branch(args.branch, switch=True, lang=lang)
            else:
                switch_branch(args.branch, lang=lang)
                
        elif args.command == 'stash':
            if args.pop:
                stash_changes(pop=True, lang=lang)
            elif args.apply:
                stash_changes(apply=True, lang=lang)
            elif args.list:
                stash_changes(list_stash=True, lang=lang)
            else:
                stash_changes(message=args.message, lang=lang)
                
        elif args.command == 'undo-commit':
            undo_last_commit(keep_changes=not args.hard, lang=lang)
            
        elif args.command == 'help' or not args.command:
            show_help(lang)
            
    except KeyboardInterrupt:
        print("\n" + ("Operation cancelled by user." if lang == 'es' else "Operación cancelada por el usuario."))
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
