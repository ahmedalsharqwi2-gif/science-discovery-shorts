def performance(plan):
 if plan['profile']!='horror':return 'Natural Egyptian Arabic, engaging conversational explanation, precise spoken numbers, not a formal announcer. No extra words. Complete the last sentence.'
 instructions=['Same approved Charon voice, natural Egyptian Arabic. DOCUMENTARY about an actual incident, not impersonation of a victim. Low intimate voiced speech, restrained fear and pauses appropriate to the words. Whisper only the narrator emphasis, never invent dialogue or screams. Every word remains clearly voiced; finish the last sentence. No added words, music or spoken directions.']
 styles={'tense':'restrained apprehension, calm control','whisper':'quiet close-mic VOICED emphasis, completely intelligible','fear':'sober concern with short pauses','panic_whisper':'hushed urgent emphasis, voiced consonants, never shout','calm':'clear grounded factual explanation','curious':'quiet investigative curiosity'}
 for scene in plan['scenes']:instructions.append('Beginning with EXACT words «'+' '.join(scene['narration'].split()[:7])+'», use '+styles[scene['delivery']]+'.')
 return '\n'.join(instructions)

