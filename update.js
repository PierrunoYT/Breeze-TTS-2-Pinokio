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
    },
    // Re-pin torch to the accelerator build. requirements.txt asks for a plain
    // torch==2.9.1, which resolves to the CPU-only wheel on Windows, so the
    // step above can undo what install.js set up. Must stay last, exactly as
    // in install.js.
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app"
        }
      }
    }
  ]
}
