# KDC USOM Multi‑Vendor Feed

USOM tarafından yayımlanan zararlı bağlantı bildirimlerini düzenli olarak toplayan, normalize eden ve farklı güvenlik duvarları için kullanılabilir metin listelerine dönüştüren self-hosted bir Python servisidir.

Bu depo yalnızca collector, kurulum betiği, örnek yapılandırmalar, testler ve systemd servislerini içerir. Canlı ortamlara ait sunucu adresleri, erişim listeleri, operasyonel süreçler ve web sitesi dosyaları bu depoya dahil edilmemiştir.

[English documentation](README.en.md)

## Desteklenen çıktı biçimleri

Örnek rota dosyası kısa ve değiştirilebilir takma adlar kullanır:

- `pa` — Palo Alto Networks
- `fg` — Fortinet FortiGate
- `sf` — Sophos Firewall
- `cp` — Check Point
- `sw` — SonicWall
- `wg` — WatchGuard

Gerçek üretim yolları Python koduna gömülü değildir. `/etc/mvfeed/routes.json` dosyasından yönetilir ve istenirse tamamen farklı adlarla kullanılabilir.

> Kısa veya tahmin edilmesi zor bir URL yolu güvenlik kontrolü değildir. Yayın dizinini TLS, ağ allowlist'i, kimlik doğrulama, rate limiting ve izleme gibi uygun kontrollerle koruyun.

## Neler yapar?

- yarım kalan ilk senkronizasyonu kaldığı yerden sürdürür
- tam aktarımda 16 worker'a kadar paralel çalışabilir
- gecikmeli kayıtları kaçırmamak için örtüşen incremental sorgular kullanır
- IPv4, IPv6, domain ve URL verilerini normalize eder
- tek veri setinden üreticiye uygun çıktı dosyaları üretir
- farklı dosya sistemlerine güvenli ve atomik yayın yapar
- SQLite ile yerel durum tutar
- systemd timer ile düzenli incremental güncelleme çalıştırır
- rolling feed yedekleri ve JSON/text durum çıktıları üretir

## Git ile kurulum

Ubuntu 24.04 ve Debian ailesi için:

```bash
git clone https://github.com/ercankskn/kdc-usom-multi-vendor-feed.git
cd kdc-usom-multi-vendor-feed
sudo bash scripts/install.sh
```

Ardından rota ve çalışma ayarlarını gözden geçirin:

```bash
sudoedit /etc/mvfeed/routes.json
sudoedit /etc/mvfeed/mvfeed.env
```

İlk tam senkronizasyonu başlatın:

```bash
sudo systemctl start mvfeed-full.service
sudo journalctl -u mvfeed-full.service -f
```

Tam senkronizasyon bittikten sonra incremental timer'ı etkinleştirin:

```bash
sudo systemctl enable --now mvfeed-sync.timer
systemctl list-timers mvfeed-sync.timer --all
```

## Temel komutlar

```bash
sudo -u mvfeed /usr/bin/python3 /opt/mvfeed/app/collector.py status
sudo -u mvfeed /usr/bin/python3 /opt/mvfeed/app/collector.py publish
sudo systemctl start mvfeed-sync.service
```

## Rota yapılandırması

`config/routes.example.json`, normalize edilmiş veri kümelerini göreli çıktı yollarıyla eşleştirir:

```json
{
  "status_prefix": "core",
  "outputs": {
    "wg/ip.txt": "all_ip",
    "wg/fqdn.txt": "domain"
  }
}
```

Desteklenen kaynak kümeleri:

- `ipv4`
- `ipv6`
- `ipv6net`
- `domain`
- `url`
- `all_ip`

## Test

```bash
python3 -m py_compile src/collector.py
python3 -m unittest discover -s tests -v
```

GitHub Actions aynı kontrolleri her push ve pull request için çalıştırır.

## Depo sınırları

Bu depoya şunları eklemeyin:

- canlı host adları ve public IP adresleri
- gerçek müşteri veya kuruma özel bilgiler
- erişim anahtarları, tokenlar, sertifikalar ve private key'ler
- üretimde kullanılan gizli rota adları
- reverse proxy ve cloud firewall yapılandırmaları
- web sitesi ve onay süreci dosyaları

## Lisans

Bu ilk taslak için henüz bir açık kaynak lisansı seçilmemiştir. Başkalarının kodu kullanmasını, değiştirmesini veya dağıtmasını istiyorsanız yayın duyurusundan önce uygun bir lisans ekleyin. Ayrıntı için [LICENSE-NOTICE.md](LICENSE-NOTICE.md) dosyasına bakın.

## Güvenlik

Bir güvenlik açığını herkese açık issue olarak paylaşmayın. Bildirim yöntemi ve dağıtım notları için [SECURITY.md](SECURITY.md) dosyasını okuyun.
