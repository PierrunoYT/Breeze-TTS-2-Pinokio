module.exports = {
  run: [
    // Clone the official Breeze TTS 2 inference code (Apache 2.0)
    {
      method: "shell.run",
      params: {
        message: [
          "git clone https://github.com/breezeblue-ai/breeze-tts app"
        ]
      }
    },
    // Add the Gradio web UI. The upstream repo ships only a CLI and a raw PCM
    // streaming API, so the launcher supplies its own UI instead of patching
    // any of the cloned project files.
    {
      method: "fs.copy",
      params: {
        src: "breeze_webui.py",
        dest: "app/breeze_webui.py"
      }
    },
    // Install the project dependencies plus gradio for the web UI
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
    // Reinstall torch against the platform's accelerator (requirements.txt
    // pins a plain torch==2.9.1, which is CPU-only on Windows)
    {
      method: "script.start",
      params: {
        uri: "torch.js",
        params: {
          venv: "env",
          path: "app"
        }
      }
    },
    // Download the Breeze TTS 2 checkpoint (~7.7GB)
    {
      method: "hf.download",
      params: {
        path: "app",
        "_": [ "BreezeBlue/Breeze-TTS-2" ],
        "local-dir": "breeze-tts-2"
      }
    },
    {
      method: "notify",
      params: {
        html: "Installation finished! Click the 'Start' tab to launch the web UI."
      }
    }
  ]
}
