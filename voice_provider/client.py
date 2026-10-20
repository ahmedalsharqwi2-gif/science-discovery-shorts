"""Approved VoiceTut in an isolated interpreter. Errors never choose another voice."""
from pathlib import Path
import json,os,subprocess,tempfile
ROOT=Path(__file__).resolve().parent.parent
def config():
    c=json.loads((ROOT/"config/accepted_voice.json").read_text())
    if c.get("provider")!="voicetut" or c.get("speaker")!="Mohammed" or c.get("fallback_allowed") is not False:
        raise ValueError("Accepted voice configuration was replaced or allows fallback")
    return c
def generate(text,output_path):
    text=" ".join(str(text).split())
    if not text:raise ValueError("Narration is empty")
    output=Path(output_path).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    c=config();interpreter=os.getenv("VOICETUT_PYTHON","").strip()
    if not interpreter:raise RuntimeError("Install voice_provider/install.sh; VOICETUT_PYTHON is required. No replacement voice will be used.")
    output.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="approved-voice-") as tmp:
        request=Path(tmp)/"request.json"
        request.write_text(json.dumps({"text":text,"output":str(output),"config":c},ensure_ascii=False),encoding="utf8")
        subprocess.run([interpreter,str(ROOT/"voice_provider/synthesize.py"),"--request",str(request)],check=True,timeout=int(os.getenv("VOICETUT_TIMEOUT_SECONDS","7200")))
    if not output.is_file() or output.stat().st_size<1000:raise RuntimeError("VoiceTut did not produce a valid recording")
    return output
