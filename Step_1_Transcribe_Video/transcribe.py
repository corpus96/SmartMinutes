from faster_whisper import WhisperModel

def transcribe_audio(audio_path):
    """
    Transcribes audio and returns a list of segments with timestamps.

    Output format:
    [
        {
            "start": float,
            "end": float,
            "text": str
        },
        ...
    ]
    """

    #Creating faster_whisper model
    model = WhisperModel(
        "small",
        device="cpu",
        compute_type="int8"
    )

    """     The beam_size parameter is set to 5, 
        which suggests that the method is using a beam search algorithm with a beam width of 5. 
        Beam search is a heuristic search algorithm that explores a graph by expanding the most promising nodes. In the context of transcription, 
        this means that the model will consider the top 5 most likely hypotheses at each step of the decoding process, which can improve the accuracy of the transcription.

        The final parameter, word_timestamps, 
        is set to False, indicating that the method should not return timestamps for each word in the transcription. 
        This could be useful if the user is only interested in the text output and not in the timing information, 
        which can be beneficial for applications where timing is not critical. """
    segments, _ = model.transcribe(
        str(audio_path),
        beam_size=5,
        word_timestamps=False
    )

    results = []

    for segment in segments:
        results.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        })

    return results