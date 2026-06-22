# Check Point

Check Point tarafında External Network Feed ile External IOC / Custom Intelligence Feed farklı iş akışlarıdır. Seçilecek yöntem, sürüme ve etkin Software Blade'lere göre belirlenmelidir.

## Üretilecek dosya

```bash
python3 scripts/generate-firewall-config.py \
  --vendor cp \
  --base-url https://feed.example.com:8443
```

## Uygulama özeti

1. IP listesi için desteklenen External Network Feed veya IOC feed akışını belirleyin.
2. Domain/URL listelerinde beklenen formatı doğrulayın; plain text, CSV ve STIX birbirinin yerine kullanılamaz.
3. HTTPS sertifikası güvenini Security Gateway tarafında kontrol edin.
4. Cluster kullanıyorsanız her ilgili member'ın feed kaynağına erişebildiğini doğrulayın.
5. Import/test ekranında kayıtları gördükten sonra policy install yapın.

## Dikkat

Bu repo, Check Point'e özel CSV/STIX şeması üretmediği için generic plain-list URL'lerini doğrudan her IOC akışına uygun varsaymaz.

Resmî kaynaklar:
https://sc1.checkpoint.com/documents/R82/WebAdminGuides/EN/CP_R82_SecurityManagement_AdminGuide/Content/Topics-SECMG/Network_Feed.htm
https://sc1.checkpoint.com/documents/R82/WebAdminGuides/EN/CP_R82_ThreatPrevention_AdminGuide/Content/Topics-TPG/Importing-External-Custom-Intelligence-Feeds-in-SmartConsole.htm
