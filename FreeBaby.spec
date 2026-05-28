# -*- mode: python ; coding: utf-8 -*-
import os

block_cipher = None
src = r'F:\FreeBaby'

a = Analysis(
    [os.path.join(src, 'launch.pyw')],
    pathex=[src],
    binaries=[],
    datas=[
        (os.path.join(src, 'frontends'), 'frontends'),
        (os.path.join(src, 'assets'), 'assets'),
        (os.path.join(src, 'scripts'), 'scripts'),
        (os.path.join(src, 'reflect'), 'reflect'),
        (os.path.join(src, 'plugins'), 'plugins'),
        (os.path.join(src, 'extensions'), 'extensions'),
        (os.path.join(src, 'agentmain.py'), '.'),
        (os.path.join(src, 'agent_loop.py'), '.'),
        (os.path.join(src, 'agent_utils.py'), '.'),
        (os.path.join(src, 'llmcore.py'), '.'),
        (os.path.join(src, 'ga.py'), '.'),
        (os.path.join(src, 'simphtml.py'), '.'),
        (os.path.join(src, 'TMWebDriver.py'), '.'),
    ],
    hiddenimports=['webview', 'streamlit', 'openai', 'requests', 'json', 'socket', 'argparse'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio',
        'onnxruntime', 'onnx',
        'cv2', 'opencv',
        'polars',
        'llvmlite', 'numba',
        'pyarrow',
        'av', 'av.libs',
        'transformers',
        'sklearn', 'scipy',
        'matplotlib', 'plotly',
        'sympy',
        'IPython', 'ipykernel', 'ipywidgets',
        'notebook', 'jupyter',
        'pytest', 'unittest',
        'tkinter', '_tkinter',
        'test', 'tests',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FreeBaby',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FreeBaby',
)