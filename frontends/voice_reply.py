"""
voice_reply.py - 小四语音回复模块
功能: 文字 → Edge TTS → MP3 → PCM → Silk → 微信语音消息
依赖: edge-tts, pysilk, ffmpeg
"""
import os
import asyncio
import tempfile
import subprocess
import edge_tts
import pysilk

# TTS 配置
DEFAULT_VOICE = "zh-CN-XiaoyiNeural"  # 中文女声
DEFAULT_RATE = "+0%"  # 语速

# 音频参数
SAMPLE_RATE = 24000  # silk 推荐采样率


def text_to_silk(text: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> bytes:
    """
    将文字转换为 silk 格式语音数据
    返回: silk 二节数据
    """
    # wechatapp.py removes HTTPS_PROXY for WeChat SSL; restore for Edge TTS
    import io as _io
    _saved_https = os.environ.get('HTTPS_PROXY', '')
    _saved_http = os.environ.get('HTTP_PROXY', '')
    _proxy = 'http://127.0.0.1:10808'
    os.environ['HTTPS_PROXY'] = _proxy
    os.environ['HTTP_PROXY'] = _proxy
    
    tmp_dir = tempfile.mkdtemp()
    mp3_path = os.path.join(tmp_dir, "tts.mp3")
    pcm_path = os.path.join(tmp_dir, "tts.pcm")
    
    try:
        # Step 1: Edge TTS → MP3
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        asyncio.run(communicate.save(mp3_path))
        
        # Step 2: FFmpeg MP3 → PCM (16-bit, 24000Hz, mono)
        subprocess.run([
            "ffmpeg", "-y", "-i", mp3_path,
            "-f", "s16le", "-ar", str(SAMPLE_RATE), "-ac", "1", pcm_path
        ], capture_output=True, check=True)
        
        # Step 3: PCM → Silk (pysilk.encode needs file-like objects)
        import io as _io
        with open(pcm_path, "rb") as f:
            pcm_data = f.read()
        silk_data = pysilk.encode(_io.BytesIO(pcm_data), _io.BytesIO(), SAMPLE_RATE)
        
        return silk_data
    
    finally:
        # 恢复原始代理设置
        if _saved_https:
            os.environ['HTTPS_PROXY'] = _saved_https
        else:
            os.environ.pop('HTTPS_PROXY', None)
        if _saved_http:
            os.environ['HTTP_PROXY'] = _saved_http
        else:
            os.environ.pop('HTTP_PROXY', None)
        # 清理临时文件
        for f in [mp3_path, pcm_path]:
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(tmp_dir)
        except OSError:
            pass


def text_to_silk_file(text: str, output_path: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> str:
    """
    将文字转换为 silk 文件并保存
    返回: silk 文件路径
    """
    silk_data = text_to_silk(text, voice, rate)
    with open(output_path, "wb") as f:
        f.write(silk_data)
    return output_path


# 可用中文语音列表
VOICES = {
    "xiaoyi": "zh-CN-XiaoyiNeural",      # 女声 活泼
    "xiaoxiao": "zh-CN-XiaoxiaoNeural",   # 女声 温暖
    "yunxi": "zh-CN-YunxiNeural",         # 男声 阳光
    "yunjian": "zh-CN-YunjianNeural",     # 男声 沉稳
}