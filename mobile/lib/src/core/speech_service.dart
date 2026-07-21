import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_to_text.dart';

abstract interface class SpeechService {
  bool get isListening;
  Future<bool> start({
    required void Function(String text) onText,
    required void Function(String message) onError,
    required void Function(bool listening) onListeningChanged,
  });
  Future<void> stop();
}

class DeviceSpeechService implements SpeechService {
  final SpeechToText _speech = SpeechToText();

  @override
  bool get isListening => _speech.isListening;

  @override
  Future<bool> start({
    required void Function(String text) onText,
    required void Function(String message) onError,
    required void Function(bool listening) onListeningChanged,
  }) async {
    final available = await _speech.initialize(
      onError: (SpeechRecognitionError error) => onError(error.errorMsg),
      onStatus: (status) => onListeningChanged(status == 'listening'),
    );
    if (!available) {
      onError('Thiết bị chưa cấp quyền hoặc không hỗ trợ nhận dạng giọng nói.');
      return false;
    }
    await _speech.listen(
      onResult: (result) => onText(result.recognizedWords),
      listenOptions: SpeechListenOptions(
        localeId: 'en_US',
        partialResults: true,
        cancelOnError: true,
        listenMode: ListenMode.dictation,
      ),
    );
    onListeningChanged(true);
    return true;
  }

  @override
  Future<void> stop() => _speech.stop();
}
