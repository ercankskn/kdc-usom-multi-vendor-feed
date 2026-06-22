# Fortinet FortiGate

FortiGate External Connectors, HTTP/HTTPS üzerinden IP Address ve Domain Name feed'lerini periyodik olarak çekebilir. Bu repodaki üretici şablonu, güvenli bir başlangıç CLI konfigürasyonu üretir.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor fg \
  --base-url https://feed.example.com:8443 \
  --object-prefix USOM \
  --interval 15
```

Ana çıktı: `fortigate-cli.conf`

## Uygulama özeti

1. Şablondaki kategori numaralarının ortamınızda kullanılmadığını doğrulayın.
2. CLI dosyasını satır satır inceleyin.
3. `Security Fabric > External Connectors` altında IP ve domain connector durumunu kontrol edin.
4. `View Entries` ile kayıtları doğrulayın.
5. Oluşturulan nesneleri yalnızca gerekli policy/profile içinde kullanın.

## Dikkat

- `server-identity-check full` korunur; kapatılması önerilmez.
- URL feed çıktısı ayrıca yayımlanır ancak her FortiOS sürümünde aynı External Connector tipiyle doğrudan kullanılamaz; web filter akışınızı sürüme göre doğrulayın.
- Multi-VDOM ortamında connector kapsamını doğru VDOM'da oluşturun.

Resmî kaynak:
https://docs.fortinet.com/document/fortigate/8.0.0/administration-guide/379433/configuring-an-external-feed
