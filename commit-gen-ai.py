import os
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
import sys
import re
import textwrap

# Configuración de formato para mensajes de commit
COMMIT_FORMAT_CONFIG = {
    "format_rules": {
        "subject": {
            "max_length": 50,
            "imperative": True,
            "capitalize": True,
            "no_period": True
        },
        "body": {
            "wrap_length": 72,
            "paragraph_spacing": True,
            "explain_what_why": True
        },
        "breaking_changes": {
            "prefix": "BREAKING CHANGE: ",
            "required_for_major_version": True
        },
        "footer": {
            "issue_references": "Soluciona: #{issue}",
            "wrap_length": 72
        }
    },
    "commit_types": [
        {"value": "feat", "name": "feat:     Una nueva característica", "description": "La nueva característica que agregas a una aplicación en particular"},
        {"value": "fix", "name": "fix:      Un parche para un error", "description": "Un parche para un error"},
        {"value": "style", "name": "style:    Características o actualizaciones relacionadas con estilos", "description": "Características o actualizaciones relacionadas con estilos"},
        {"value": "refactor", "name": "refactor: Refactorizar una sección específica de la base de código", "description": "Refactorizar una sección específica de la base de código"},
        {"value": "test", "name": "test:     Todo lo relacionado con pruebas", "description": "Todo lo relacionado con pruebas"},
        {"value": "docs", "name": "docs:     Todo lo relacionado con documentación", "description": "Todo lo relacionado con documentación"},
        {"value": "chore", "name": "chore:    Mantenimiento de código regular", "description": "Mantenimiento de código regular"},
        {"value": "perf", "name": "perf:     Mejoras de rendimiento", "description": "Un cambio de código que mejora el rendimiento"},
        {"value": "build", "name": "build:    Cambios que afectan el sistema de compilación o dependencias externas", "description": "Cambios que afectan el sistema de compilación o dependencias externas"},
        {"value": "ci", "name": "ci:       Cambios en la configuración de CI", "description": "Cambios en los archivos y scripts de configuración de CI"}
    ],
    "style_rules": {
        "use_imperative": "Escribe tu mensaje de commit en imperativo: 'Corregir error' y no 'Corregido error' o 'Corrige error'",
        "capitalize": "Usa mayúsculas al inicio del título y por cada párrafo del cuerpo del mensaje",
        "no_period_in_subject": "No termines el título con un punto",
        "separate_subject_body": "Separa el título del cuerpo del mensaje con una línea en blanco",
        "explain_what_why": "Usa el cuerpo del mensaje para explicar cuáles cambios has hecho y por qué los hiciste",
        "provide_context": "No asumas que las personas que revisarán el código entienden cuál era el problema original",
        "bullet_points": "Las viñetas están bien, normalmente se utiliza un guión o asterisco"
    }
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

# Historial de comandos ejecutados
command_history = []

def track_command(command, description):
    """Registra un comando ejecutado y su descripción."""
    command_history.append((command, description))

def show_command_summary(lang='en'):
    """Muestra un resumen de los comandos ejecutados."""
    if not command_history:
        return
    
    print("\n" + "="*50)
    print("Command Summary / Resumen de Comandos:")
    print("="*50)
    
    for i, (cmd, desc) in enumerate(command_history, 1):
        print(f"\n{i}. {desc}")
        print(f"   $ {cmd}")
    
    print("\n" + "="*50)
    print("You can run these commands directly in your terminal /")
    print("Puedes ejecutar estos comandos directamente en tu terminal")
    print("="*50)

def show_commit_format_rules(lang='en'):
    """Muestra las reglas de formato para los mensajes de commit."""
    print("\n" + "="*50)
    print("Commit Format Rules / Reglas de Formato de Commit:")
    print("-" * 50)
    
    # Mostrar reglas de formato según el idioma
    if lang == 'en':
        print("Subject Rules:")
        print(f"- Maximum length: {COMMIT_FORMAT_CONFIG['format_rules']['subject']['max_length']} characters")
        print("- Use imperative mood: 'Fix bug' not 'Fixed bug'")
        print("- Capitalize first letter")
        print("- No period at the end")
        print("\nBody Rules:")
        print(f"- Wrap text at {COMMIT_FORMAT_CONFIG['format_rules']['body']['wrap_length']} characters")
        print("- Separate paragraphs with blank lines")
        print("- Explain what and why, not how")
        print("- Use bullet points with hyphens or asterisks when appropriate")
        print("- Keep messages concise and direct")
        print("- Briefly mention which files were modified, added or deleted")
    else:  # Spanish
        print("Reglas para el Asunto:")
        print(f"- Longitud máxima: {COMMIT_FORMAT_CONFIG['format_rules']['subject']['max_length']} caracteres")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['use_imperative']}")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['capitalize']}")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['no_period_in_subject']}")
        print("\nReglas para el Cuerpo:")
        print(f"- Ajustar texto a {COMMIT_FORMAT_CONFIG['format_rules']['body']['wrap_length']} caracteres")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['separate_subject_body']}")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['explain_what_why']}")
        print(f"- {COMMIT_FORMAT_CONFIG['style_rules']['bullet_points']}")
        print("- Mantener los mensajes concisos y directos")
        print("- Mencionar brevemente qué archivos fueron modificados, agregados o eliminados")
    
    print("="*50)

def run_git_command(command):
    """Ejecuta un comando git con codificación UTF-8 y manejo de errores mejorado"""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando {' '.join(command)}: {e}")
        print(f"Salida de error: {e.stderr}")
        return None

def get_git_diff():
    """Get the git diff of staged changes with proper encoding handling"""
    try:
        diff = run_git_command(["git", "diff", "--staged"])
        if diff is None:
            return ""
        track_command("git diff --staged", "Show staged changes / Mostrar cambios preparados")
        return diff
    except Exception as e:
        print(f"Error inesperado obteniendo git diff: {e}")
        return ""

def show_status(lang='en'):
    """Show git repository status."""
    try:
        print("\n" + "Repository Status / Estado del Repositorio:" + "\n" + "="*50)
        status = run_git_command(["git", "status"])
        if status:
            print(status)
        track_command("git status", "Show repository status / Mostrar estado del repositorio")
    except Exception as e:
        print(f"Error showing git status: {e}")

def add_files_to_stage(files=".", lang='en'):
    """Add files to staging area."""
    try:
        if files == ".":
            run_git_command(["git", "add", "."])
            track_command("git add .", "Add all changes to staging / Añadir todos los cambios al área de staging")
            print("\n✅ All changes added to staging!" if lang == 'en' else "\n✅ ¡Todos los cambios añadidos al staging!")
        else:
            run_git_command(["git", "add", *files.split()])
            track_command(f"git add {files}", f"Add specific files to staging / Añadir archivos específicos al staging")
            print("\n✅ Files added to staging!" if lang == 'en' else "\n✅ ¡Archivos añadidos al staging!")
    except Exception as e:
        print(f"Error adding files: {e}")

def undo_changes(files=".", lang='en'):
    """Undo changes in files."""
    try:
        if files == ".":
            run_git_command(["git", "checkout", "--", "."])
            track_command("git checkout -- .", "Undo all local changes / Deshacer todos los cambios locales")
            print("\n✅ All changes undone!" if lang == 'en' else "\n✅ ¡Todos los cambios deshechos!")
        else:
            run_git_command(["git", "checkout", "--", *files.split()])
            track_command(f"git checkout -- {files}", f"Undo changes in specific files / Deshacer cambios en archivos específicos")
            print("\n✅ Changes undone in specified files!" if lang == 'en' else "\n✅ ¡Cambios deshechos en los archivos especificados!")
    except Exception as e:
        print(f"Error undoing changes: {e}")

def push_changes(branch=None, lang='en'):
    """Push changes to remote repository."""
    try:
        if not branch:
            # Get current branch
            branch = run_git_command(["git", "branch", "--show-current"])
        
        if branch:
            run_git_command(["git", "push", "origin", branch])
            track_command(f"git push origin {branch}", f"Push changes to remote / Subir cambios al repositorio remoto")
            print("\n✅ Changes pushed successfully!" if lang == 'en' else "\n✅ ¡Cambios subidos exitosamente!")
        else:
            print("Could not determine current branch." if lang == 'en' else "No se pudo determinar la rama actual.")
    except Exception as e:
        print(f"Error pushing changes: {e}")

def pull_changes(lang='en'):
    """Pull changes from remote repository."""
    try:
        run_git_command(["git", "pull"])
        track_command("git pull", "Pull changes from remote / Descargar cambios del repositorio remoto")
        print("\n✅ Changes pulled successfully!" if lang == 'en' else "\n✅ ¡Cambios descargados exitosamente!")
    except Exception as e:
        print(f"Error pulling changes: {e}")

def create_branch(branch_name, lang='en'):
    """Create a new branch."""
    try:
        run_git_command(["git", "checkout", "-b", branch_name])
        track_command(f"git checkout -b {branch_name}", f"Create and switch to new branch / Crear y cambiar a nueva rama")
        print(f"\n✅ Branch '{branch_name}' created and checked out!" if lang == 'en' 
              else f"\n✅ ¡Rama '{branch_name}' creada y seleccionada!")
    except Exception as e:
        print(f"Error creating branch: {e}")

def switch_branch(branch_name, lang='en'):
    """Switch to an existing branch."""
    try:
        run_git_command(["git", "checkout", branch_name])
        track_command(f"git checkout {branch_name}", f"Switch to branch / Cambiar a rama")
        print(f"\n✅ Switched to branch '{branch_name}'!" if lang == 'en' 
              else f"\n✅ ¡Cambiado a rama '{branch_name}'!")
    except Exception as e:
        print(f"Error switching branch: {e}")

def list_branches(lang='en'):
    """List all local branches."""
    try:
        print("\n" + "Local Branches / Ramas Locales:" + "\n" + "="*50)
        branches = run_git_command(["git", "branch"])
        if branches:
            print(branches)
        track_command("git branch", "List local branches / Listar ramas locales")
    except Exception as e:
        print(f"Error listing branches: {e}")

def stash_changes(message="", lang='en'):
    """Stash current changes."""
    try:
        if message:
            run_git_command(["git", "stash", "push", "-m", message])
            track_command(f"git stash push -m '{message}'", f"Stash changes with message / Guardar cambios temporales con mensaje")
        else:
            run_git_command(["git", "stash", "push"])
            track_command("git stash push", "Stash changes / Guardar cambios temporales")
        
        print("\n✅ Changes stashed successfully!" if lang == 'en' else "\n✅ ¡Cambios guardados temporalmente!")
    except Exception as e:
        print(f"Error stashing changes: {e}")

def apply_stash(stash_id="", lang='en'):
    """Apply stash."""
    try:
        if stash_id:
            run_git_command(["git", "stash", "apply", stash_id])
            track_command(f"git stash apply {stash_id}", f"Apply specific stash / Aplicar cambios temporales específicos")
        else:
            run_git_command(["git", "stash", "apply"])
            track_command("git stash apply", "Apply last stash / Aplicar últimos cambios temporales")
        
        print("\n✅ Stash applied successfully!" if lang == 'en' else "\n✅ ¡Cambios temporales aplicados!")
    except Exception as e:
        print(f"Error applying stash: {e}")

def revert_last_commit(lang='en'):
    """Revert the last commit."""
    try:
        run_git_command(["git", "revert", "HEAD"])
        track_command("git revert HEAD", "Revert last commit / Revertir el último commit")
        print("\n✅ Last commit reverted successfully!" if lang == 'en' else "\n✅ ¡Último commit revertido exitosamente!")
    except Exception as e:
        print(f"Error reverting commit: {e}")

def generate_commit_message(api_key, diff, commit_type, scope, lang='en'):
    """Generate a commit message using Qwen 2.5 API with proper structure based on COMMIT_FORMAT_CONFIG"""
    if not diff:
        return "No changes to commit" if lang == 'en' else "No hay cambios para hacer commit"
    
    # Forzar español para los mensajes de commit
    lang = 'es'
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Extraer reglas de formato de la configuración
    format_rules = COMMIT_FORMAT_CONFIG["format_rules"]
    style_rules = COMMIT_FORMAT_CONFIG["style_rules"]
    
    # Construir prompts basados en la configuración
    if lang == 'en':
        system_prompt = (
            "You are an expert in conventional commits. Generate complete commit messages with type, scope, subject and body "
            "following specific formatting rules. Keep messages concise and to the point."
        )
        
        # Construir reglas de formato para el prompt
        format_instructions = [
            f"- Subject: short, imperative mood, max {format_rules['subject']['max_length']} chars, capitalize first letter, no period at end",
            f"- Body: brief description wrapped at {format_rules['body']['wrap_length']} chars, separate paragraphs with blank lines",
            f"- Breaking changes: prefix with '{format_rules['breaking_changes']['prefix']}'"
        ]
        
        # Construir reglas de estilo para el prompt
        style_instructions = [
            "- Use imperative mood in the subject line",
            "- Capitalize the subject line and each paragraph",
            "- Briefly mention what files were modified, added or deleted",
            "- Keep explanations concise and direct",
            "- Use bullet points with hyphens for multiple changes"
        ]
        
        user_prompt = (
            f"Generate a concise conventional commit message for these changes. "
            f"Use type: '{commit_type}' and scope: '{scope}'. Structure:\n\n"
            "<type>(<scope>): <subject>\n\n"
            "- What was changed (brief technical description).\n"
            "- Impact/benefit (optional).\n"
            "- Reason/context (issue, feedback, etc.).\n\n"
            "Format rules:\n"
            + "\n".join(format_instructions) + "\n\n"
            "Style rules:\n"
            + "\n".join(style_instructions) + "\n\n"
            f"Changes:\n{diff}\n\n"
            "The body should be brief and direct, mentioning only the files changed and a short explanation of why."
        )
    else:  # Spanish
        system_prompt = (
            "Eres un experto en commits convencionales. Genera mensajes concisos con tipo, ámbito, asunto y cuerpo "
            "siguiendo reglas específicas de formato. Mantén los mensajes breves y directos."
        )
        
        # Construir reglas de formato para el prompt en español
        format_instructions = [
            f"- Asunto: corto, modo imperativo, máximo {format_rules['subject']['max_length']} caracteres, primera letra mayúscula, sin punto final",
            f"- Cuerpo: descripción breve ajustada a {format_rules['body']['wrap_length']} caracteres, separar párrafos con líneas en blanco",
            f"- Cambios disruptivos: prefijo con '{format_rules['breaking_changes']['prefix']}'"
        ]
        
        # Construir reglas de estilo para el prompt en español
        style_instructions = [
            "- Usa modo imperativo en la línea de asunto ('Corregir error' no 'Corregido error')",
            "- Usa mayúscula en la primera letra del asunto y de cada párrafo",
            "- Menciona brevemente qué archivos fueron modificados, agregados o eliminados",
            "- Mantén las explicaciones concisas y directas",
            "- Usa viñetas con guiones para múltiples cambios"
        ]
        
        user_prompt = (
            f"Genera un mensaje de commit convencional conciso para estos cambios. "
            f"Usa tipo: '{commit_type}' y ámbito: '{scope}'. Estructura:\n\n"
            "<tipo>(<ámbito>): <título>\n\n"
            "- Qué se cambió (técnico breve).\n"
            "- Impacto/beneficio (opcional).\n"
            "- Motivo/contexto (issue, feedback, etc.).\n\n"
            "Reglas de formato:\n"
            + "\n".join(format_instructions) + "\n\n"
            "Reglas de estilo:\n"
            + "\n".join(style_instructions) + "\n\n"
            f"Cambios:\n{diff}\n\n"
            "El cuerpo debe ser breve y directo, mencionando solo los archivos cambiados y una explicación corta del por qué."
        )
    
    data = {
        "model": "qwen/qwen2.5-vl-72b-instruct:free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 300,  # Reducido para forzar mensajes más concisos
        "temperature": 0.5,
        "stop": ["<|im_end|>"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error generating commit message: {e}")
        return ""

def get_commit_type(lang='en'):
    """Get the type of commit based on standards."""
    print("\n" + (COMMIT_MESSAGES["type"] if lang == 'en' else COMMIT_MESSAGES_ES["type"]))
    for i, t in enumerate(COMMIT_TYPES, 1):
        print(f"{i}. {t['name']}")
    
    while True:
        try:
            choice = int(input("\nEnter number / Ingresa el número: ")) - 1
            if 0 <= choice < len(COMMIT_TYPES):
                return COMMIT_TYPES[choice]["value"]
            print("Invalid choice. Please try again." if lang == 'en' else "Opción inválida. Inténtalo de nuevo.")
        except ValueError:
            print("Please enter a valid number." if lang == 'en' else "Por favor, ingresa un número válido.")

def get_language_choice():
    """Ask user to choose a language."""
    while True:
        choice = input("\nChoose language / Elige idioma (en/es): ").strip().lower()
        if choice in ['en', 'es']:
            return choice
        print("Invalid choice. Please enter 'en' or 'es'.")

def get_commit_scope(lang='en'):
    """Get the scope of the changes."""
    prompt = COMMIT_MESSAGES["scope"] if lang == 'en' else COMMIT_MESSAGES_ES["scope"]
    scope = input(f"\n{prompt} ").strip()
    return scope if scope else ""

def get_commit_body(lang='en'):
    """Get the body of the commit message."""
    prompt = COMMIT_MESSAGES["body"] if lang == 'en' else COMMIT_MESSAGES_ES["body"]
    print(f"\n{prompt}")
    body = input().strip()
    # Reemplazar | con saltos de línea
    return body.replace("|", "\n")

def get_commit_breaking(lang='en'):
    """Get breaking changes information."""
    prompt = COMMIT_MESSAGES["breaking"] if lang == 'en' else COMMIT_MESSAGES_ES["breaking"]
    print(f"\n{prompt}")
    breaking = input().strip()
    return f"BREAKING CHANGE: {breaking}" if breaking else ""

def get_commit_footer(lang='en'):
    """Get footer information (issues closed)."""
    prompt = COMMIT_MESSAGES["footer"] if lang == 'en' else COMMIT_MESSAGES_ES["footer"]
    print(f"\n{prompt}")
    footer = input().strip()
    return f"Closes: {footer}" if footer else ""

def format_commit_message(commit_type, scope, subject, body="", breaking="", footer=""):
    """Format the commit message according to conventional commit standards and COMMIT_FORMAT_CONFIG rules."""
    # Obtener reglas de formato
    format_rules = COMMIT_FORMAT_CONFIG["format_rules"]
    
    # Aplicar reglas de formato al asunto
    # 1. Asegurar que comienza con mayúscula
    if subject and format_rules["subject"]["capitalize"]:
        subject = subject[0].upper() + subject[1:] if len(subject) > 0 else subject
    
    # 2. Eliminar punto final si existe
    if subject and format_rules["subject"]["no_period"] and subject.endswith("."):
        subject = subject[:-1]
    
    # 3. Limitar longitud del asunto
    max_subject_length = format_rules["subject"]["max_length"]
    if len(subject) > max_subject_length:
        subject = subject[:max_subject_length]
    
    # Formatear el encabezado
    if scope:
        header = f"{commit_type}({scope}): {subject}"
    else:
        header = f"{commit_type}: {subject}"
    
    # Formatear el cuerpo con ajuste de texto y separación de párrafos
    formatted_body = ""
    if body:
        # Dividir el cuerpo en párrafos
        paragraphs = body.split("\n\n")
        wrapped_paragraphs = []
        
        for paragraph in paragraphs:
            # Verificar si es una lista con viñetas
            if paragraph.strip().startswith("-") or paragraph.strip().startswith("*"):
                # Procesar cada línea de la lista manteniendo las viñetas
                lines = paragraph.split("\n")
                wrapped_lines = []
                for line in lines:
                    if line.strip().startswith("-") or line.strip().startswith("*"):
                        # Es una viñeta, ajustar con sangría
                        indent = " " * 2  # 2 espacios de sangría después de la viñeta
                        bullet = line.strip()[0] + " "  # La viñeta y un espacio
                        text = line.strip()[2:].strip()  # El texto después de la viñeta
                        # Ajustar el texto con sangría para las líneas adicionales
                        wrapped_text = textwrap.fill(text, 
                                                    width=format_rules["body"]["wrap_length"]-len(bullet)-len(indent),
                                                    subsequent_indent=indent+" "*len(bullet))
                        wrapped_lines.append(bullet + wrapped_text)
                    else:
                        # No es una viñeta, ajustar normalmente
                        wrapped_lines.append(textwrap.fill(line, width=format_rules["body"]["wrap_length"]))
                wrapped_paragraphs.append("\n".join(wrapped_lines))
            else:
                # Párrafo normal, ajustar a la longitud especificada
                wrapped_paragraphs.append(textwrap.fill(paragraph, width=format_rules["body"]["wrap_length"]))
        
        # Unir los párrafos con doble salto de línea
        formatted_body = "\n\n".join(wrapped_paragraphs)
    
    # Formatear los cambios disruptivos
    formatted_breaking = breaking
    if breaking and not breaking.startswith(format_rules["breaking_changes"]["prefix"]):
        formatted_breaking = format_rules["breaking_changes"]["prefix"] + breaking
    
    # Formatear el pie de página
    formatted_footer = footer
    if footer and "#" in footer and "Soluciona" not in footer and "Closes" not in footer:
        # Intentar formatear referencias a issues si no están ya formateadas
        issue_refs = re.findall(r'#(\d+)', footer)
        if issue_refs:
            formatted_refs = [format_rules["footer"]["issue_references"].replace("{issue}", ref) for ref in issue_refs]
            formatted_footer = "\n".join(formatted_refs)
    
    # Construir el mensaje completo
    message_parts = [header]
    
    # Agregar cuerpo si existe
    if formatted_body:
        message_parts.append("")
        message_parts.append(formatted_body)
    
    # Agregar breaking changes si existen
    if formatted_breaking:
        if not formatted_body:  # Si no hay cuerpo, agregar línea en blanco después del encabezado
            message_parts.append("")
        message_parts.append(formatted_breaking)
    
    # Agregar footer si existe
    if formatted_footer:
        if not formatted_body and not formatted_breaking:  # Si no hay cuerpo ni breaking changes, agregar línea en blanco
            message_parts.append("")
        message_parts.append(formatted_footer)
    
    return "\n".join(message_parts)

def get_commit_by_id(commit_id, lang='en'):
    """Get commit information by its ID."""
    try:
        # Verificar que el commit existe
        if not run_git_command(["git", "rev-parse", "--verify", commit_id]):
            print(f"Commit con ID {commit_id} no encontrado" if lang == 'es' else f"Commit with ID {commit_id} not found")
            return None
        
        # Obtener el mensaje del commit
        commit_message = run_git_command(["git", "log", "-1", "--pretty=%B", commit_id])
        
        # Obtener el diff del commit
        try:
            diff = run_git_command(["git", "show", commit_id, "--name-status", "--pretty=format:"])
        except:
            # Intentar con otro enfoque si el anterior falla
            parent_commit = run_git_command(["git", "rev-parse", f"{commit_id}^"])
            if parent_commit:
                diff = run_git_command(["git", "diff", parent_commit, commit_id])
            else:
                diff = ""
        
        return {
            "id": commit_id,
            "message": commit_message or "",
            "diff": diff or ""
        }
    except Exception as e:
        print(f"Error obteniendo commit: {e}")
        return None

def edit_commit_manually(commit_id, lang='en'):
    """Edit a commit message manually."""
    try:
        # Obtener el mensaje actual del commit
        commit_message = run_git_command(["git", "log", "-1", "--pretty=%B", commit_id])
        
        if commit_message is None:
            print(f"No se pudo obtener el mensaje del commit {commit_id}" if lang == 'es' else f"Could not get commit message for {commit_id}")
            return
        
        print("\n" + "="*50)
        print(f"Current commit message ({commit_id}):" if lang == 'en' else f"Mensaje actual del commit ({commit_id}):")
        print("-" * 50)
        print(commit_message)
        print("="*50)
        
        # Editar manualmente
        print("\nEnter your new commit message (press Enter twice to finish):" if lang == 'en' 
              else "\nIngresa el nuevo mensaje de commit (presiona Enter dos veces para terminar):")
        lines = []
        while True:
            line = input()
            if not line and (not lines or not lines[-1]):
                break
            lines.append(line)
        
        new_message = "\n".join(lines)
        
        if not new_message.strip():
            print("Empty message. Operation cancelled." if lang == 'en' else "Mensaje vacío. Operación cancelada.")
            return
        
        print("\n" + "="*50)
        print("New commit message:" if lang == 'en' else "Nuevo mensaje de commit:")
        print("-" * 50)
        print(new_message)
        print("="*50)
        
        # Confirmar cambio
        confirm = input("\nApply this change? (y/n): " if lang == 'en' 
                     else "¿Aplicar este cambio? (s/n): ").strip().lower()
        
        if confirm in ['y', 's']:
            # Si es el último commit, usar --amend
            head_commit = run_git_command(["git", "rev-parse", "HEAD"])
            
            if commit_id == head_commit or commit_id.startswith(head_commit) or head_commit.startswith(commit_id):
                run_git_command(["git", "commit", "--amend", "-m", new_message])
                track_command(f"git commit --amend -m \"{new_message}\"", "Amend last commit / Modificar último commit")
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
                parent_commit = run_git_command(["git", "rev-parse", f"{commit_id}^"])
                
                if not parent_commit:
                    print("No se pudo obtener el commit padre" if lang == 'es' else "Could not get parent commit")
                    return
                
                print("Starting interactive rebase..." if lang == 'en' else "Iniciando rebase interactivo...")
                run_git_command(["git", "rebase", "-i", "--exec", f"git commit --amend -m '{new_message}' && git rebase --continue", parent_commit])
                track_command(f"git rebase -i {parent_commit}", "Interactive rebase to edit commit / Rebase interactivo para editar commit")
                
                # Eliminar el script temporal
                if script_path.exists():
                    os.remove(script_path)
            
            print("\n✅ Commit message updated successfully!" if lang == 'en' 
                  else "\n✅ ¡Mensaje de commit actualizado correctamente!")
    except Exception as e:
        print(f"Error: {e}")
        print("Operation failed. Make sure the commit exists and you have permission to modify it." if lang == 'en'
              else "La operación falló. Asegúrate de que el commit existe y tienes permisos para modificarlo.")

def rename_last_commit(api_key, lang='en'):
    """Rename the last commit if it hasn't been pushed yet, following format rules."""
    try:
        # Check if there are any commits to rename
        run_git_command(["git", "log", "-1"])
        
        # Get the current commit message
        old_message = run_git_command(["git", "log", "-1", "--pretty=%B"])
        
        if old_message is None:
            print("No se pudo obtener el último mensaje de commit" if lang == 'es' else "Could not get last commit message")
            return
        
        # Mostrar reglas de formato al usuario
        show_commit_format_rules(lang)
        
        print("\n" + "="*50)
        print("Last commit message:" if lang == 'en' else "Último mensaje de commit:")
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
            print("Operation cancelled." if lang == 'en' else "Operación cancelada.")
            return
        
        if edit_choice == 'M':
            # Obtener el ID del último commit
            head_commit = run_git_command(["git", "rev-parse", "HEAD"])
            if head_commit:
                # Editar manualmente
                edit_commit_manually(head_commit, lang)
            return
        
        # Generate new message with AI
        print("\nGenerating new commit message..." if lang == 'en' else "\nGenerando nuevo mensaje de commit...")
        
        # Get the diff of the last commit
        try:
            diff = run_git_command(["git", "show", "HEAD", "--name-status", "--pretty=format:"])
        except:
            # Intentar con otro enfoque si el anterior falla
            diff = run_git_command(["git", "diff", "HEAD~1", "HEAD"])
        
        if not diff:
            print("No se pudo obtener el diff del último commit" if lang == 'es' else "Could not get last commit diff")
            return
        
        # Get commit type and scope
        commit_type = get_commit_type(lang)
        scope = get_commit_scope(lang)
        
        # Generate message with AI
        ai_message = generate_commit_message(api_key, diff, commit_type, scope, lang)
        
        if not ai_message:
            print("Failed to generate commit message" if lang == 'en' 
                  else "Error al generar el mensaje de commit")
            return
        
        print("\n" + "="*50)
        print("New commit message:" if lang == 'en' else "Nuevo mensaje de commit:")
        print("-" * 50)
        print(ai_message)
        print("="*50)
        
        # Ask for confirmation
        confirm = input("\nApply this change? (y/n): " if lang == 'en' 
                     else "¿Aplicar este cambio? (s/n): ").strip().lower()
        
        if confirm in ['y', 's']:
            run_git_command(["git", "commit", "--amend", "-m", ai_message])
            track_command(f"git commit --amend -m \"{ai_message}\"", "Amend last commit with new message / Modificar último commit con nuevo mensaje")
            print("\n✅ Commit message updated successfully!" if lang == 'en' 
                  else "\n✅ ¡Mensaje de commit actualizado correctamente!")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have at least one commit to rename." if lang == 'en'
              else "Asegúrate de tener al menos un commit para renombrar.")

def create_new_commit(api_key, lang='en'):
    """Create a new commit with AI-generated full message following format rules"""
    # Mostrar reglas de formato al usuario
    show_commit_format_rules(lang)
    print("\n")
    
    # Añadir automáticamente todos los cambios al área de staging
    print("Adding all changes to staging area..." if lang == 'en' else "Añadiendo todos los cambios al área de staging...")
    add_files_to_stage(".", lang)
    
    # Get git diff
    diff = get_git_diff()
    if not diff:
        print("No changes to commit" if lang == 'en' else "No hay cambios para hacer commit")
        return
    
    # Get commit type and scope
    commit_type = get_commit_type(lang)
    scope = get_commit_scope(lang)
    
    # Generate full commit message with AI
    print("\nGenerating full commit message..." if lang == 'en' else "\nGenerando mensaje de commit completo...")
    formatted_message = generate_commit_message(api_key, diff, commit_type, scope, lang)
    
    if not formatted_message:
        print("Failed to generate commit message" if lang == 'en' else "Error al generar el mensaje de commit")
        return
    
    # Historial de mensajes generados
    message_history = [formatted_message]
    current_index = 0
    
    while True:
        # Mostrar el mensaje formateado
        print("\n" + "="*50)
        print("Commit message:" if lang == 'en' else "Mensaje de commit:")
        print("-" * 50)
        print(formatted_message)
        print("="*50)
        
        # Mostrar opciones
        print("\nOptions / Opciones:")
        print("(A) Accept and commit / Aceptar y hacer commit")
        print("(R) Regenerate message / Regenerar mensaje")
        print("(E) Edit manually / Editar manualmente")
        print("(C) Cancel / Cancelar")
        
        choice = input("\nEnter your choice / Ingresa tu opción: ").strip().upper()
        
        if choice == 'A':  # Aceptar y hacer commit
            try:
                run_git_command(["git", "commit", "-m", formatted_message])
                track_command(f"git commit -m \"{formatted_message}\"", "Create new commit / Crear nuevo commit")
                print("\n✅ Commit created successfully!" if lang == 'en' else "\n✅ ¡Commit creado exitosamente!")
                break
            except Exception as e:
                print(f"Error creating commit: {e}" if lang == 'en' else f"Error al crear el commit: {e}")
                break
        
        elif choice == 'R':  # Regenerar mensaje
            print("\nRegenerating commit message..." if lang == 'en' else "\nRegenerando mensaje de commit...")
            new_message = generate_commit_message(api_key, diff, commit_type, scope, lang)
            if new_message:
                formatted_message = new_message
                message_history.append(new_message)
                current_index = len(message_history) - 1
            else:
                print("Failed to regenerate message" if lang == 'en' else "Error al regenerar el mensaje")
        
        elif choice == 'E':  # Editar manualmente
            print("\nCurrent commit message / Mensaje actual:" if lang == 'en' else "\nMensaje actual:")
            print("-" * 50)
            print(formatted_message)
            print("-" * 50)
            
            print("\nEnter your commit message (press Enter twice to finish):" if lang == 'en' 
                  else "\nIngresa tu mensaje de commit (presiona Enter dos veces para terminar):")
            lines = []
            while True:
                line = input()
                if not line and (not lines or not lines[-1]):
                    break
                lines.append(line)
            
            formatted_message = "\n".join(lines)
            
            # Guardar en historial
            message_history.append(formatted_message)
            current_index = len(message_history) - 1
        
        elif choice == 'C':  # Cancelar
            print("Commit cancelled." if lang == 'en' else "Commit cancelado.")
            break
        
        else:
            print("Invalid option. Please try again." if lang == 'en' else "Opción inválida. Inténtalo de nuevo.")

def edit_specific_commit(api_key, lang='en'):
    """Edit a specific commit by its ID, following format rules."""
    # Mostrar reglas de formato al usuario
    show_commit_format_rules(lang)
    
    # Mostrar los últimos commits para referencia
    print("\nShowing last 10 commits for reference:" if lang == 'en' else "\nMostrando los últimos 10 commits como referencia:")
    logs = run_git_command(["git", "log", "--oneline", "-n", "10"])
    if logs:
        print(logs)
    
    # Solicitar ID del commit
    commit_id = input("\nEnter commit ID / Ingresa el ID del commit: ").strip()
    
    if not commit_id:
        print("Operation cancelled." if lang == 'en' else "Operación cancelada.")
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
        print("Operation cancelled." if lang == 'en' else "Operación cancelada.")
        return
    
    if edit_choice == 'M':
        # Editar manualmente
        edit_commit_manually(commit_id, lang)
        return
    
    # Edición asistida por IA
    # Get commit type and scope
    commit_type = get_commit_type(lang)
    scope = get_commit_scope(lang)
    
    # Generate message with AI
    print("\nGenerating new commit message..." if lang == 'en' else "\nGenerando nuevo mensaje de commit...")
    ai_message = generate_commit_message(api_key, commit_info["diff"], commit_type, scope, lang)
    
    if not ai_message:
        print("Failed to generate commit message" if lang == 'en' 
              else "Error al generar el mensaje de commit")
        return
    
    print("\n" + "="*50)
    print("New commit message:" if lang == 'en' else "Nuevo mensaje de commit:")
    print("-" * 50)
    print(ai_message)
    print("="*50)
    
    # Ask for confirmation
    confirm = input("\nApply this change? (y/n): " if lang == 'en' 
                 else "¿Aplicar este cambio? (s/n): ").strip().lower()
    
    if confirm in ['y', 's']:
        # Si es el último commit, usar --amend
        head_commit = run_git_command(["git", "rev-parse", "HEAD"])
        
        if commit_id == head_commit or commit_id.startswith(head_commit) or head_commit.startswith(commit_id):
            run_git_command(["git", "commit", "--amend", "-m", ai_message])
            track_command(f"git commit --amend -m \"{ai_message}\"", "Amend last commit / Modificar último commit")
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
            parent_commit = run_git_command(["git", "rev-parse", f"{commit_id}^"])
            
            if not parent_commit:
                print("No se pudo obtener el commit padre" if lang == 'es' else "Could not get parent commit")
                return
            
            print("Starting interactive rebase..." if lang == 'en' else "Iniciando rebase interactivo...")
            run_git_command(["git", "rebase", "-i", "--exec", f"git commit --amend -m '{ai_message}' && git rebase --continue", parent_commit])
            track_command(f"git rebase -i {parent_commit}", "Interactive rebase to edit commit / Rebase interactivo para editar commit")
            
            # Eliminar el script temporal
            if script_path.exists():
                os.remove(script_path)
        
        print("\n✅ Commit message updated successfully!" if lang == 'en' 
              else "\n✅ ¡Mensaje de commit actualizado correctamente!")

def git_management_menu(api_key, lang='en'):
    """Show the git management menu."""
    while True:
        print("\n" + "="*50)
        print("Git Management Menu / Menú de Gestión de Git")
        print("="*50)
        print("1. Repository Status / Estado del Repositorio")
        print("2. Add Changes to Staging / Añadir Cambios al Staging")
        print("3. Undo Changes / Deshacer Cambios")
        print("4. Push Changes / Subir Cambios")
        print("5. Pull Changes / Descargar Cambios")
        print("6. Branch Management / Gestión de Ramas")
        print("7. Stash Management / Gestión de Stash")
        print("8. Revert Last Commit / Revertir Último Commit")
        print("9. Return to Main Menu / Volver al Menú Principal")
        
        choice = input("\nEnter your choice (1-9): ").strip()
        
        if choice == '1':
            show_status(lang)
        elif choice == '2':
            print("\nAdd files to staging / Añadir archivos al staging:")
            print("(A) Add all changes / Añadir todos los cambios")
            print("(S) Add specific files / Añadir archivos específicos")
            print("(C) Cancel / Cancelar")
            
            add_choice = input("\nEnter your choice: ").strip().upper()
            
            if add_choice == 'A':
                add_files_to_stage(".", lang)
            elif add_choice == 'S':
                files = input("Enter file paths (space separated): ").strip()
                add_files_to_stage(files, lang)
        elif choice == '3':
            print("\nUndo changes / Deshacer cambios:")
            print("(A) Undo all changes / Deshacer todos los cambios")
            print("(S) Undo specific files / Deshacer archivos específicos")
            print("(C) Cancel / Cancelar")
            
            undo_choice = input("\nEnter your choice: ").strip().upper()
            
            if undo_choice == 'A':
                undo_changes(".", lang)
            elif undo_choice == 'S':
                files = input("Enter file paths (space separated): ").strip()
                undo_changes(files, lang)
        elif choice == '4':
            branch = input("Enter branch name (leave empty for current branch): ").strip()
            push_changes(branch if branch else None, lang)
        elif choice == '5':
            pull_changes(lang)
        elif choice == '6':
            print("\nBranch Management / Gestión de Ramas:")
            print("(L) List branches / Listar ramas")
            print("(C) Create new branch / Crear nueva rama")
            print("(S) Switch branch / Cambiar de rama")
            print("(R) Return / Regresar")
            
            branch_choice = input("\nEnter your choice: ").strip().upper()
            
            if branch_choice == 'L':
                list_branches(lang)
            elif branch_choice == 'C':
                branch_name = input("Enter new branch name: ").strip()
                create_branch(branch_name, lang)
            elif branch_choice == 'S':
                branch_name = input("Enter branch name to switch to: ").strip()
                switch_branch(branch_name, lang)
        elif choice == '7':
            print("\nStash Management / Gestión de Stash:")
            print("(S) Stash changes / Guardar cambios temporales")
            print("(A) Apply stash / Aplicar cambios temporales")
            print("(R) Return / Regresar")
            
            stash_choice = input("\nEnter your choice: ").strip().upper()
            
            if stash_choice == 'S':
                message = input("Enter stash message (optional): ").strip()
                stash_changes(message, lang)
            elif stash_choice == 'A':
                stash_id = input("Enter stash ID (leave empty for last stash): ").strip()
                apply_stash(stash_id if stash_id else None, lang)
        elif choice == '8':
            revert_last_commit(lang)
        elif choice == '9':
            break
        else:
            print("Invalid choice. Please try again." if lang == 'en' else "Opción inválida. Inténtalo de nuevo.")
        
        show_command_summary(lang)

def main():
    # Forzar configuración regional para UTF-8
    os.environ['LC_ALL'] = 'C.UTF-8'
    os.environ['LANG'] = 'C.UTF-8'
    
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
    
    while True:
        # Clear command history for new operation
        command_history.clear()
        
        # Ask user what they want to do
        print("\n" + "="*50)
        print("Main Menu / Menú Principal")
        print("="*50)
        print("1. Git Management / Gestión de Git")
        print("2. Create a new commit / Crear un nuevo commit")
        print("3. Rename last commit / Renombrar el último commit")
        print("4. Edit specific commit by ID / Editar commit específico por ID")
        print("5. Exit / Salir")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == '1':
            git_management_menu(api_key, lang)
        elif choice == '2':
            create_new_commit(api_key, lang)
            show_command_summary(lang)
        elif choice == '3':
            rename_last_commit(api_key, lang)
            show_command_summary(lang)
        elif choice == '4':
            edit_specific_commit(api_key, lang)
            show_command_summary(lang)
        elif choice == '5':
            print("\nGoodbye! / ¡Hasta luego!")
            break
        else:
            print("Invalid choice. Please try again." if lang == 'en' else "Opción inválida. Inténtalo de nuevo.")

if __name__ == "__main__":
    main()