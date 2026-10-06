def explain(event):
    kind = event["type"]
    quote = event["quote"]
    if kind == "pace":
        direction = "compressed" if event["delta"]<0 else "lengthened"
        event["interpretation"] = f'The matched phrase "{quote}" is {direction} relative to the reference beyond the accepted engineering tolerance. This is a delivery difference requiring context, not a claim about intent.'
        event["suggestion"] = ("Allow more elapsed time and retain clause boundaries." if direction=="compressed" else "Shorten the phrase while preserving articulation and clause boundaries.")
    elif kind == "intonation":
        event["interpretation"] = f'The voiced pitch range in "{quote}" is contracted despite sufficient variation in the reference.'
        event["suggestion"] = "Increase pitch contrast on meaningful words; keep your natural median pitch."
    elif kind == "energy":
        event["interpretation"] = f'Relative energy contrast in "{quote}" is lower than the reference after removing microphone gain offsets.'
        event["suggestion"] = "Vary emphasis across meaningful words rather than increasing whole-file volume."
    elif kind == "pauses":
        direction = "longer" if event["delta"]>0 else "shorter"
        event["interpretation"] = f'The VAD-supported gap between "{quote}" is {direction} than the corresponding reference boundary.'
        event["suggestion"] = "Rehearse this boundary with a deliberate clause pause; judge its length in rhetorical context."
    else:
        event["interpretation"] = "The audio contains a recording-quality concern. This is not evidence of poor articulation."
        event["suggestion"] = "Re-record with headroom and reduced interference before judging vocal delivery."
    return event
