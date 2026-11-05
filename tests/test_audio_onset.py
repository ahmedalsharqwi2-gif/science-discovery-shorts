import wave,pytest
from remotion_factory.locked_episode import validate_first_audio_frame

def test_silent_first_frame_is_rejected(tmp_path):
 p=tmp_path/'silent.wav'
 with wave.open(str(p),'wb') as w:w.setparams((1,2,48000,0,'NONE','not compressed'));w.writeframes(bytes(9600))
 with pytest.raises(ValueError,match='no audible speech'):validate_first_audio_frame(p)
