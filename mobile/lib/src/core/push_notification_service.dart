import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import 'api_client.dart';

typedef PushMessageCallback = void Function(String title, String body);

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // The operating system displays notification payloads while the app is in
  // the background. Data-only messages can be handled here after the app has
  // a durable local notification policy.
}

class PushNotificationService {
  PushNotificationService({this.onForegroundMessage});

  final PushMessageCallback? onForegroundMessage;
  StreamSubscription<String>? _tokenSubscription;
  StreamSubscription<RemoteMessage>? _messageSubscription;
  String? _registeredToken;
  bool _initialized = false;

  Future<void> initialize(ApiClient apiClient) async {
    if (_initialized || !_isSupportedPlatform) return;
    _initialized = true;

    try {
      await Firebase.initializeApp();
      final messaging = FirebaseMessaging.instance;
      final permission = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        provisional: true,
      );
      if (permission.authorizationStatus == AuthorizationStatus.denied) return;

      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
      _messageSubscription = FirebaseMessaging.onMessage.listen(
        (message) => onForegroundMessage?.call(
          message.notification?.title ?? 'LearnMate',
          message.notification?.body ?? '',
        ),
      );
      _tokenSubscription = messaging.onTokenRefresh.listen(
        (token) => _registerToken(apiClient, token),
      );
      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _registerToken(apiClient, token);
      }
    } catch (_) {
      // Firebase native files are intentionally environment-specific and are
      // not committed. Until they exist, in-app notifications remain the
      // reliable fallback.
    }
  }

  Future<void> _registerToken(ApiClient apiClient, String token) async {
    if (token == _registeredToken || apiClient.accessToken == null) return;
    try {
      await apiClient.registerPushDevice(token: token, platform: _platform);
      _registeredToken = token;
    } on ApiException {
      // Registration retries on the next token refresh or app start.
    } catch (_) {
      // Push must never block the learning experience.
    }
  }

  Future<void> dispose() async {
    await _tokenSubscription?.cancel();
    await _messageSubscription?.cancel();
    _tokenSubscription = null;
    _messageSubscription = null;
    _registeredToken = null;
  }

  bool get _isSupportedPlatform =>
      !kIsWeb &&
      (defaultTargetPlatform == TargetPlatform.android ||
          defaultTargetPlatform == TargetPlatform.iOS);

  String get _platform =>
      defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';
}
