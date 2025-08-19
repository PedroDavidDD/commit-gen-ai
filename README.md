# Generador de Mensajes de Commit con IA

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub](https://img.shields.io/badge/Repo-GitHub-success)](https://github.com/PedroDavidDD/commit-gen-ai)

Una herramienta de línea de comandos que te ayuda a generar mensajes de commit bien formateados siguiendo el estándar [Conventional Commits](https://www.conventionalcommits.org/), con la asistencia de IA (Qwen 2.5).

## 🌟 Características

- 🤖 Generación de mensajes de commit con IA
- 🌍 Soporte bilingüe (Español/Inglés)
- 📝 Sigue el estándar Conventional Commits
- 🔄 Edición interactiva de mensajes
- 🔍 Herramientas de gestión de repositorios Git
- 📊 Historial y resumen de comandos
- 🎯 Validación y sugerencias de tipos de commit

## 🚀 Comenzando

### Requisitos Previos

- Python 3.8 o superior
- Git instalado en tu sistema
- Clave API de Qwen 2.5 (regístrate en [Qwen](https://qwen.ai/))

### Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/PedroDavidDD/commit-gen-ai.git
   cd commit-gen-ai
   ```

2. Instala las dependencias necesarias:
   ```bash
   pip install requests python-dotenv
   ```

3. Crea un archivo `.env` en la raíz del proyecto con tu API key:
   ```
   QWEN_API_KEY=tu_api_key_aquí
   ```

## 🛠 Uso

Ejecuta el script:
```bash
python commit-gen-ai.py
```

### Características Principales

1. **Nuevo Commit**
   - Generación interactiva de mensajes
   - Sugerencias de IA basadas en tus cambios
   - Formateo automático según Conventional Commits

2. **Editar Commit Existente**
   - Editar el commit más reciente
   - Editar cualquier commit por su ID
   - Rebase interactivo para commits ya subidos

3. **Gestión del Repositorio**
   - Añadir/remover cambios al staging
   - Ver estado del repositorio
   - Gestión de ramas
   - Manejo de stashes
   - Enviar/recibir cambios

## 📚 Formato del Mensaje de Commit

Esta herramienta sigue el siguiente formato de mensaje de commit:

```
<tipo>(<ámbito>): <asunto>
[LÍNEA EN BLANCO]
[cuerpo]
[LÍNEA EN BLANCO]
[pie de página]
```

### Tipos de Commit

- `feat`: Una nueva característica
- `fix`: Una corrección de error
- `docs`: Cambios en la documentación
- `style`: Cambios que no afectan el significado del código
- `refactor`: Cambios que no corrigen errores ni agregan características
- `perf`: Mejoras de rendimiento
- `test`: Agregar o corregir pruebas
- `build`: Cambios que afectan el sistema de compilación
- `ci`: Cambios en la configuración de CI/CD
- `chore`: Otros cambios que no modifican archivos fuente

## 🌍 Soporte de Idiomas

El script soporta tanto español como inglés. Se te preguntará tu idioma preferido al inicio.

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Siéntete libre de enviar un Pull Request.

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

## 📬 Contacto

- GitHub: [@PedroDavidDD](https://github.com/PedroDavidDD)
- Repositorio: [PedroDavidDD/commit-gen-ai](https://github.com/PedroDavidDD/commit-gen-ai)

---

<div align="center">
  Hecho con ❤️ por Pedro David
</div>
