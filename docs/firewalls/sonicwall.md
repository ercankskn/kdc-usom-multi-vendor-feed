# SonicWall

SonicOS Dynamic External Address Group (DEAG), HTTPS üzerindeki IP veya FQDN listelerini periyodik olarak çekebilir. IP ve FQDN için ayrı DEAG oluşturulmalıdır.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor sw \
  --base-url https://feed.example.com:8443
```

## Uygulama özeti

1. `OBJECT > Match Objects > Dynamic Group` bölümüne gidin.
2. IP listesi için FQDN seçeneği kapalı bir DEAG oluşturun.
3. Domain listesi için FQDN seçeneği açık ayrı bir DEAG oluşturun.
4. Üretilen HTTPS URL'lerini girin ve refresh ayarını sürüme göre yapılandırın.
5. Dynamic External Address Objects üyelerini doğrulayın.
6. Grupları sınırlı kapsamlı access rule içinde kullanın.

## Dikkat

- DEAG/DEAO limitleri model ve firmware'e göre değişir.
- Threat API ayrı bir push yöntemidir; bu şablon onu etkinleştirmez.

Resmî kaynak:
https://www.sonicwall.com/support/technical-documentation/docs/sonicos-7-1-objects/Content/Match_Objects/Dynamic_Group/about-deag-file.htm
