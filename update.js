module.exports = {
  run: [
    // Update the launcher
    {
      method: "shell.run",
      params: {
        message: "git pull"
      }
    },
    // Update the cloned Breeze TTS 2 code
    {
      method: "shell.run",
      params: {
        path: "app",
        message: "git pull"
      }
    },
    // Refresh the web UI with the latest version from the launcher
    {
      method: "fs.copy",
      params: {
        src: "breeze_webui.py",
        dest: "app/breeze_webui.py"
      }
    },
    // Pick up any dependency changes
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        message: [
          "uv pip install -r requirements.txt",
          "uv pip install gradio"
        ]
      }
    }
  ]
}
