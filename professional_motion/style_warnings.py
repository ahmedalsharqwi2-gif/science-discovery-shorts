"""Editorial preferences are review notes, never substitutes for media checks."""
def note(story,message):
    warnings=story.setdefault('editorial_warnings',[])
    if not isinstance(warnings,list):warnings=[];story['editorial_warnings']=warnings
    if message not in warnings:warnings.append(message)
