import 'package:flutter/foundation.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';

abstract interface class OcrService {
  bool get isSupported;
  Future<String?> recognize(ImageSource source);
}

class MlKitOcrService implements OcrService {
  MlKitOcrService({ImagePicker? imagePicker})
    : _imagePicker = imagePicker ?? ImagePicker();

  final ImagePicker _imagePicker;

  @override
  bool get isSupported =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.android ||
          defaultTargetPlatform == TargetPlatform.iOS);

  @override
  Future<String?> recognize(ImageSource source) async {
    if (!isSupported) {
      throw UnsupportedError('OCR camera chỉ hỗ trợ Android và iOS.');
    }
    final file = await _imagePicker.pickImage(
      source: source,
      imageQuality: 90,
      maxWidth: 2048,
    );
    if (file == null) return null;

    final recognizer = TextRecognizer(script: TextRecognitionScript.latin);
    try {
      final image = InputImage.fromFilePath(file.path);
      final result = await recognizer.processImage(image);
      return result.text.trim();
    } finally {
      await recognizer.close();
    }
  }
}
