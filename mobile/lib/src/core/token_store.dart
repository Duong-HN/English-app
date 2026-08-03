import 'package:flutter_secure_storage/flutter_secure_storage.dart';

abstract interface class TokenStore {
  Future<String?> read();
  Future<String?> readRefresh();
  Future<void> write(String token, {String? refreshToken});
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  const SecureTokenStore();

  static const _key = 'learnmate_access_token';
  static const _refreshKey = 'learnmate_refresh_token';
  static const _storage = FlutterSecureStorage();

  @override
  Future<String?> read() => _storage.read(key: _key);

  @override
  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  @override
  Future<void> write(String token, {String? refreshToken}) async {
    await _storage.write(key: _key, value: token);
    if (refreshToken == null || refreshToken.isEmpty) {
      await _storage.delete(key: _refreshKey);
    } else {
      await _storage.write(key: _refreshKey, value: refreshToken);
    }
  }

  @override
  Future<void> clear() async {
    await _storage.delete(key: _key);
    await _storage.delete(key: _refreshKey);
  }
}

class MemoryTokenStore implements TokenStore {
  String? token;
  String? refreshToken;

  @override
  Future<void> clear() async {
    token = null;
    refreshToken = null;
  }

  @override
  Future<String?> read() async => token;

  @override
  Future<String?> readRefresh() async => refreshToken;

  @override
  Future<void> write(String value, {String? refreshToken}) async {
    token = value;
    this.refreshToken = refreshToken;
  }
}
