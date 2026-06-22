# WatchGuard

Bu proje WatchGuard için IP ve FQDN metin listeleri üretir. Firebox/Fireware sürümleri ve yönetim yöntemleri arasında tek bir evrensel native pull akışı varsayılmaz.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor wg \
  --base-url https://feed.example.com:8443
```

## Uygulama özeti

1. Kullanılan Fireware ve yönetim platformunda desteklenen import/API yöntemini belirleyin.
2. Üretilen IP ve FQDN URL'lerini normal bir istemciyle doğrulayın.
3. Mevcut otomasyon katmanınız feed'i çekiyorsa format ve kayıt limitlerini test edin.
4. Önce test policy'si veya sınırlı bir alias/list üzerinde uygulayın.
5. Blocked Sites/alias değişiklikleri için rollback prosedürü tutun.

## Dikkat

Bu kit doğrudan cihazda değişiklik yapmaz ve her sürüm için desteklenmeyen bir native connector iddiasında bulunmaz.

WatchGuard dokümantasyon merkezi:
https://www.watchguard.com/help/docs/help-center/en-US/
