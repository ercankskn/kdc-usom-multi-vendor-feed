# Sophos Firewall

Sophos Firewall Third-party threat feeds özelliği; IPv4, domain ve URL göstergelerini ayrı feed kaynaklarından alabilir.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor sf \
  --base-url https://feed.example.com:8443
```

## Uygulama özeti

1. `Active threat response > Third-party threat feeds` bölümünü açın.
2. IPv4, domain ve URL için üç ayrı feed oluşturun.
3. Üretilen kaynak URL'lerini ve desteklenen polling aralığını girin.
4. Her feed'i bir kez `Synchronize now` ile çekin.
5. Sayaçları ve örnek göstergeleri kontrol ettikten sonra etkinleştirin.

## Dikkat

- Özelliğin görünürlüğü ve enforcement davranışı sürüm/lisans paketine bağlı olabilir.
- HTTPS sertifikasının cihaz tarafından güvenilir olduğundan emin olun.
- İlk testte yanlış pozitif etkisini sınırlamak için kontrollü kapsam kullanın.

Resmî kaynak:
https://docs.sophos.com/nsg/sophos-firewall/22.0/Help/en-us/webhelp/onlinehelp/AdministratorHelp/ActiveThreatResponse/ConfigureFeeds/ThirdPartyThreatFeeds/
