"""Motion Kit-inspired timeline contract for reproducible 9:16 episodes.
No API calls; this is an edit decision list, not a 3D renderer.
"""
import json
from pathlib import Path

PALETTES = {
 "science":{"accent":"#46C9F7","style":"diagrammatic-science"},
 "history":{"accent":"#E3B675","style":"historical-archive"},
 "horror":{"accent":"#B65959","style":"restrained-suspense"},
 "news":{"accent":"#37DDC6","style":"kinetic-news"},
}
MOTIONS = {"science":"diagram-reveal","history":"map-reveal","horror":"shadow-reveal","news":"headline-reveal"}
def timeline(timing, profile):
    if profile not in PALETTES: raise ValueError("Unknown motion profile")
    duration=float(timing["duration"])
    if not 0 < duration <= 180:raise ValueError("Invalid duration")
    words=timing.get("words",[])
    scenes=timing.get("scenes",[])
    result={"schema":"motion-kit-timeline-v1","profile":profile,
            "format":{"width":1080,"height":1920,"fps":30,"safe_margin_x":110,"safe_margin_bottom":340},
            "art_direction":PALETTES[profile],"duration":duration,
            "events":[],"words":[]}
    for word in words:
        start=float(word.get("start",0));end=float(word.get("end",start))
        if not 0<=start<=end<=duration+.15:raise ValueError("Invalid word timing")
        result["words"].append({"text":str(word.get("text","")),"start":start,"end":end})
    for i,scene in enumerate(scenes):
        start=float(scene.get("start",0));end=float(scene.get("end",duration))
        if not 0<=start<end<=duration+.25:raise ValueError("Invalid scene timing")
        result["events"].append({"at":start,"end":end,"type":"scene_transition",
          "motion":MOTIONS[profile],"scene":i,"intensity":"low" if profile=="horror" else "medium"})
        beat=scene.get("beat")
        if beat is not None and start<=float(beat)<end:
            result["events"].append({"at":float(beat),"type":"emphasis","scene":i,
              "motion":"pulse" if profile!="horror" else "light-flicker"})
    return result

def save(timing,profile,destination="output/motion_kit_timeline.json"):
    p=Path(destination);p.parent.mkdir(parents=True,exist_ok=True)
    data=timeline(timing,profile)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    return data
