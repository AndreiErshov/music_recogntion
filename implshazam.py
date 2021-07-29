from ShazamAPI import Shazam
from pydub import AudioSegment


class ImplShazam(Shazam):
    def __init__(self):
        self.MAX_TIME_SECONDS = 8

    def recognizeAudioSegment(self, segment: AudioSegment) -> dict:
        assert segment.frame_rate == 16000, 'Frame rate must be 16000'
        assert segment.channels == 1, 'AudioSegment must be mono channel'
        assert segment.sample_width == 2, 'Sample width must be 2'
        self.audio = segment
        signatureGenerator = self.createSignatureGenerator(self.audio)
        while True:

            signature = signatureGenerator.get_next_signature()
            if not signature:
                break

            results = self.sendRecognizeRequest(signature)
            currentOffset = signatureGenerator.samples_processed / 16000

            yield currentOffset, results
