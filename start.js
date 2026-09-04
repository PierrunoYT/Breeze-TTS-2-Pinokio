module.exports = {
  daemon: true,
  run: [
    {
      method: "shell.run",
      params: {
        venv: "env",
        path: "app",
        env: {
          GRADIO_SERVER_NAME: "127.0.0.1"
        },
        message: [
          "python breeze_webui.py"
        ],
        on: [{
          // Capture the Gradio URL so pinokio.js can show the "Open Web UI" tab
          "event": "/(http:\/\/[0-9.:]+)/",
          "done": true
        }]
      }
    },
    {
      method: "local.set",
      params: {
        url: "{{input.event[1]}}"
      }
    }
  ]
}
