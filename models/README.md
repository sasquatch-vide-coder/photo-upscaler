# Model Files

Place `.pth` or `.safetensors` model files in this directory.

## Quick Start

Run the following to download starter models:

```bash
upscaler models download --all
```

Or download specific models:

```bash
upscaler models list --available
upscaler models download RealESRGAN_x4plus
```

## Supported Architectures

Any model supported by [Spandrel](https://github.com/chaiNNer-org/spandrel) will work, including:

- **Real-ESRGAN** (x2, x4, anime variants)
- **SwinIR** (classical SR, lightweight, real-world)
- **DAT** (Dual Aggregation Transformer)
- **ESRGAN / BSRGAN / SRFormer / OmniSR** and 30+ more

## Manual Download

Download models from [OpenModelDB](https://openmodeldb.info/) and place the `.pth` or `.safetensors` file directly in this folder.

Spandrel will auto-detect the architecture and scale factor from the model weights.
