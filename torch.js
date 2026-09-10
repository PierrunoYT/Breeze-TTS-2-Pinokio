// Installs the accelerator build of torch/torchaudio.
// Breeze TTS 2 pins torch==2.9.1 and torchaudio==2.9.1 in requirements.txt,
// but the PyPI wheels are CPU-only on Windows, so the versions are reinstalled
// here from the CUDA index. torchvision is not used by this project.
//
// Windows uses --no-deps because those wheels ship their own CUDA DLLs and do
// not need the nvidia-* PyPI packages; the Linux wheels do, so that branch
// resolves dependencies normally. Because --no-deps also means pip will not
// re-resolve torch, any later `uv pip install -r requirements.txt` can pull
// the CPU wheel back in — which is why install.js and update.js both end by
// re-running this script.
module.exports = {
  run: [
    // nvidia windows
    {
      "when": "{{gpu === 'nvidia' && platform === 'win32'}}",
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          "uv pip install torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128 --force-reinstall --no-deps"
        ]
      },
      "next": null
    },
    // nvidia linux
    {
      "when": "{{gpu === 'nvidia' && platform === 'linux'}}",
      "method": "shell.run",
      "params": {
        "bluefairy": "off",
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": [
          "uv pip install torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128 --force-reinstall"
        ]
      },
      "next": null
    },
    // cpu fallback (Breeze TTS 2 needs CUDA to be usable, but keep the venv consistent)
    {
      "method": "shell.run",
      "params": {
        "venv": "{{args && args.venv ? args.venv : null}}",
        "path": "{{args && args.path ? args.path : '.'}}",
        "message": "uv pip install torch==2.9.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cpu --force-reinstall --no-deps"
      }
    }
  ]
}
