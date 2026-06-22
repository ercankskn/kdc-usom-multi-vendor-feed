# Palo Alto Networks

Palo Alto Networks, web sunucusunda tutulan IP, domain ve URL metin dosyalarını External Dynamic List (EDL) nesnesi olarak çekebilir. Her kayıt ayrı satırda olmalıdır.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor pa \
  --base-url https://feed.example.com:8443
```

Çıktı, IP List, Domain List ve URL List için ayrı nesne planı üretir.

## Uygulama özeti

1. `Objects > External Dynamic Lists` bölümünde üç ayrı EDL oluşturun.
2. Üretilen IP, domain ve URL adreslerini ilgili listelere verin.
3. Management/service route üzerinden feed hostuna erişimi doğrulayın.
4. Imported entries görünümünden kayıtların geldiğini kontrol edin.
5. EDL nesnelerini uygun Security, URL Filtering veya Anti-Spyware/DNS Security politikasına sınırlı kapsamda ekleyin.
6. Commit edin ve logları izleyin.

## Dikkat

- HTTPS sunucu sertifikası doğrulamasını açık tutun.
- Domain ve URL listeleri aynı policy davranışını sağlamaz; doğru nesne tipini seçin.
- Model, lisans ve PAN-OS sürümüne göre limitleri kontrol edin.

Resmî kaynak:
https://docs.paloaltonetworks.com/network-security/security-policy/administration/objects/external-dynamic-lists
