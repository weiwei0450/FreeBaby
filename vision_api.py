import base64, requests, sys, os
from io import BytesIO
from pathlib import Path

# ============ FreeBaby vision_api ============
# 图片识别模块，支持多个后端
# 从 mykey.py 读取配置，与 GenericAgent 兼容
# =============================================

# ModelScope 免费视觉模型（默认后端，无需额外配置）
MODELSCOPE_API_BASE = 'https://api-inference.modelscope.cn'
MODELSCOPE_MODEL = 'Qwen/Qwen3-VL-235B-A22B-Instruct'

# 默认后端选择
# 'modelscope' - 免费，每天2000次，支持图片
# 'openai' - 从mykey.py读取第一个native_oai配置（需要模型支持图片）
# 'github' - 需要mykey.py中有oai_config_gpt41mini
DEFAULT_BACKEND = 'modelscope'

_DIR = os.path.dirname(os.path.abspath(__file__))
for _p in [_DIR, os.path.join(_DIR, '..')]:
    if _p not in sys.path: sys.path.insert(0, _p)


def ask_vision(image_input, prompt="Describe this image in detail", timeout=60, max_pixels=1440000, backend=None):
    """Analyze an image using vision-capable LLM.
    
    Args:
        image_input: file path (str/Path) or PIL Image
        prompt: question about the image
        timeout: API timeout in seconds
        max_pixels: resize if larger
        backend: 'modelscope'/'openai'/'github'/None (use DEFAULT_BACKEND)
    
    Returns:
        str: description or error message
    """
    if backend is None:
        backend = DEFAULT_BACKEND
    
    try:
        b64 = _prepare_image(image_input, max_pixels)
    except Exception as e:
        return f"Error: image processing failed - {type(e).__name__}: {e}"
    
    try:
        if backend == 'modelscope':
            return _call_openai_compat(
                b64, prompt, timeout,
                apibase=MODELSCOPE_API_BASE,
                apikey=_get_ms_key(),
                model=MODELSCOPE_MODEL,
            )
        elif backend == 'openai':
            cfg = _get_oai_config()
            return _call_openai_compat(
                b64, prompt, timeout,
                apibase=cfg['apibase'], apikey=cfg['apikey'], model=cfg['model'],
            )
        elif backend == 'github':
            cfg = _get_github_config()
            return _call_openai_compat(
                b64, prompt, timeout,
                apibase=cfg['apibase'], apikey=cfg['apikey'], model=cfg['model'],
            )
        else:
            return f"Error: unknown backend '{backend}', options: modelscope, openai, github"
    except requests.exceptions.Timeout:
        return f"Error: timeout (>{timeout}s)"
    except requests.exceptions.RequestException as e:
        return f"Error: API request failed - {type(e).__name__}: {e}"
    except (KeyError, ValueError) as e:
        return f"Error: response parse failed - {e}"


# ===================== config loaders =====================

def _get_ms_key():
    """Load ModelScope API key from mykey.py if available, else use default."""
    try:
        import mykey
        return getattr(mykey, 'MODELSCOPE_API_KEY', _default_ms_key())
    except Exception:
        return _default_ms_key()

def _default_ms_key():
    return os.environ.get('MODELSCOPE_API_KEY', '')

def _get_oai_config():
    """Get first OAI config from mykey.py mixin or native_oai_config."""
    import mykey
    # try mixin_config first
    mc = getattr(mykey, 'mixin_config', None)
    if mc and mc.get('llm_configs'):
        cfg = mc['llm_configs'][0]
        return {'apibase': cfg['apibase'], 'apikey': cfg['apikey'], 'model': cfg.get('model', '')}
    # fallback: first native_oai_config*
    for attr in dir(mykey):
        if attr.startswith('native_oai_config'):
            cfg = getattr(mykey, attr)
            if isinstance(cfg, dict) and 'apibase' in cfg:
                return cfg
    raise ValueError("No OAI config found in mykey.py")

def _get_github_config():
    """Get GitHub Models config from mykey.py."""
    import mykey
    cfg = getattr(mykey, 'oai_config_gpt41mini', None)
    if cfg is None:
        cfg = getattr(mykey, 'github_model_config', None)
    if cfg is None:
        raise ValueError("No GitHub model config in mykey.py (need oai_config_gpt41mini)")
    return cfg


# ===================== image processing =====================

def _prepare_image(image_input, max_pixels=1440000):
    """Load + resize + base64 encode image. Returns b64 string."""
    from PIL import Image
    if isinstance(image_input, Image.Image):
        img = image_input
    elif isinstance(image_input, (str, Path)):
        with open(image_input, 'rb') as f:
            head = f.read(30)
        if head.startswith(b'data:image/'):
            import re
            with open(str(image_input), 'r') as f:
                raw = f.read()
            match = re.match(r'data:image/[^;]+;base64,(.*)', raw, re.DOTALL)
            if match:
                img_data = base64.b64decode(match.group(1).strip())
                img = Image.open(BytesIO(img_data))
            else:
                raise ValueError("Cannot parse data URL format")
        else:
            img = Image.open(image_input)
    else:
        raise TypeError(f"image_input must be file path or PIL Image, got: {type(image_input).__name__}")
    
    w, h = img.size
    if w * h > max_pixels:
        scale = (max_pixels / (w * h)) ** 0.5
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    if img.mode in ('RGBA', 'LA', 'P'):
        rgb = Image.new('RGB', img.size, (255, 255, 255))
        rgb.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = rgb
    
    buf = BytesIO()
    img.save(buf, format='JPEG', quality=80, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return b64


# ===================== API call =====================

def _call_openai_compat(b64, prompt, timeout, *, apibase, apikey, model, proxy=None):
    """Call OpenAI-compatible vision API with base64 image."""
    proxies = {'https': proxy, 'http': proxy} if proxy else None
    base = apibase.rstrip('/')
    if not base.endswith('/v1'):
        base += '/v1'
    
    resp = requests.post(
        base + '/chat/completions',
        json={'model': model, 'messages': [{
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
            ]
        }]},
        headers={'Authorization': f'Bearer {apikey}', 'Content-Type': 'application/json'},
        proxies=proxies, timeout=timeout
    )
    resp.raise_for_status()
    return resp.json()['choices'][0]['message']['content']


if __name__ == '__main__':
    pass
