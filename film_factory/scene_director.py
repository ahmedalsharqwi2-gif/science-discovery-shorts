"""Audio-driven cinematic shot decisions; deterministic, no paid APIs.

A cue is an instruction to an asset-backed compositor, not a claim that a
photograph or a line drawing constitutes a simulated action.
"""
import re
import unicodedata

CUES={
 "history":(
  ("artillery",r"مدفع|مدافع|قذيف|قصف|قنبل|انفجار|بارود",("artillery_fire","muzzle_flash","smoke_plume"),"cannon_boom"),
  ("march",r"جنود|جيش|قوات|معرك|هجوم|فرسان|خيول|اشتباك",("character_rig_march","terrain_tracking","dust_simulation"),"battlefield"),
  ("map",r"خريط|حدود|حصار|تحرك|انسحاب|مسار",("geo_map_camera","route_reveal","terrain_extrusion"),"map_sweep"),
 ),
 "science":(
  ("neuron",r"عصب|اعصاب|عصبون|اشار|كهرب|مخ|دماغ",("neuron_morphology","impulse_propagation","macro_dolly"),"electric_pulse"),
  ("biology",r"خلية|خلايا|بكتيري|حمض|بروتين|جين",("microscopy_depth","molecule_motion","focus_pull"),"microscopic_whoosh"),
  ("space",r"كوكب|مدار|مجر|ثقب|جاذبي|نجوم",("orbital_mechanics","scale_camera","depth_parallax"),"deep_space"),
 ),
 "horror":(
  ("apparition",r"شبح|ظل|رعب|صوت|صرخ|خطوات",("environment_occlusion","practical_light_sweep","focus_pull"),"dark_ambience"),
  ("mystery",r"اختف|غموض|ليل|منار|باب|سلم",("location_dolly","fog_layers","volumetric_light"),"suspense_riser"),
 ),
 "news":(
  ("processor",r"معالج|شريح|رقاق|حاسوب|ذكاء|نموذج",("chip_macro","material_reveal","data_flow"),"electronic_riser"),
  ("compare",r"مقارن|سرع|نسب|اختبار|نتائج|ارقام",("data_driven_chart","numeric_interpolation","camera_reframe"),"data_tick"),
 ),
}
DEFAULT={"science":("scientific_subject","asset_backed_macro","designed_transition"),
         "history":("historical_location","archive_camera","location_transition"),
         "horror":("physical_environment","practical_light","slow_reveal"),
         "news":("documented_subject","product_flythrough","clean_cut")}
def normalize(text):
 text=unicodedata.normalize("NFKC",str(text or ""))
 return re.sub(r"[\u064b-\u065f\u0670ـ]","",text).lower().replace("أ","ا").replace("إ","ا").replace("آ","ا")
def shots(timing,profile):
 if profile not in CUES:raise ValueError("Unsupported shot profile")
 words=timing.get("words",[])
 scenes=timing.get("scenes",[])
 result=[]
 for i,s in enumerate(scenes):
  start=float(s["start"]);end=float(s["end"])
  matched=[(float(w["start"]),w["text"]) for w in words if start<=float(w.get("start",-1))<end]
  text=" ".join(t for _,t in matched) or str(s.get("title",""))
  norm=normalize(text)
  spec=next(((name,visual,sound) for name,pat,visual,sound in CUES[profile] if re.search(pat,norm)),None)
  kind,visual,sound=spec if spec else (DEFAULT[profile][0],(DEFAULT[profile][1],DEFAULT[profile][2]),"subtle_transition")
  trigger=next((when for when,word in matched if any(re.search(pat,normalize(word)) for name,pat,_,_ in CUES[profile] if name==kind)),start)
  result.append({"scene":i,"start":start,"end":end,"subject":kind,
    "assets_required":list(visual),"cue_at":trigger,"sound":sound,
    "quality_gate":"animated_subject_or_verified_footage",
    "no_flat_shapes":True,"no_static_photo_as_action":True})
 return result
