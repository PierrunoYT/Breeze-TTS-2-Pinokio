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
    // Repair incomplete checkpoints and pick up model file updates.
    {
      method: "hf.download",
      params: {
        path: "app",
        "_": [ "BreezeBlue/Breeze-TTS-2" ],
        "local-dir": "breeze-tts-2"
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
