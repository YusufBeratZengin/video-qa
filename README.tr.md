# video-qa

Yayınlamadan önce render edilmiş videolara yerel kalite kontrolü uygular.
Donmuş görüntü, siyah bölümler, eksik veya sessiz ses, kırpılma riski taşıyan
ses tepeleri, ses yüksekliği ve çözünürlük/fps/süre sapmalarını kontrol eder.
Remotion veya FFmpeg ile video üreten iş akışlarında CI kontrolü olarak kullanılabilir.

[English](README.md) · [Katkı rehberi](CONTRIBUTING.md) · [Değişiklikler](CHANGELOG.md)

## Kurulum

Python 3.10 veya üzeri ve PATH üzerinde **ffmpeg ile ffprobe** gerekir.
FFmpeg dağıtımınız `freezedetect`, `blackdetect`, `silencedetect`, `astats` ve
`loudnorm` filtrelerini içermelidir.
[FFmpeg indirme sayfasından](https://ffmpeg.org/download.html) uygun dağıtımı seçebilirsiniz.

Depo klasöründe:

```console
python -m pip install .
video-qa check out.mp4 --profile shorts
```

`python -m pip install '.[ffmpeg]'`, PATH üzerinde FFmpeg yoksa `imageio-ffmpeg`
paketinin ikilisini kullanmayı sağlar. **Bu ek paket ffprobe içermez**; ffprobe'u
ayrıca kurun. İkili yollarını `--ffmpeg` ve `--ffprobe` ile verebilirsiniz.

İşlem bilgisayarınızda çalışır; video yüklenmez, API çağrılmaz, çalışma sırasında
ikili indirilmez ve kaynak video değiştirilmez. FFmpeg girdilerinde ağ protokolleri
kapalıdır. Raporlar dosya yolunu ve bazen çözücü hata mesajlarını içerir;
paylaşmadan önce gözden geçirin.

## Kullanım

```console
video-qa check out.mp4 --profile shorts --max-freeze 1.5 --target-lufs -14
video-qa check out.mp4 --profile reels --max-duration 120 --max-silence 1
video-qa check out.mp4 --profile tiktok --format json --output report.json
video-qa check out.mp4 --profile examples/custom.toml --format junit --output junit.xml
python -m video_qa check out.mp4 --max-black 0.25 --timeout 600
```

Varsayılan çıktı, PASS/WARN/FAIL satırlarından oluşan bir tablodur.
`--format json` veya `--format junit` aynı sonuçları makine tarafından okunabilir
biçimde verir. `--output` kullanılırsa yalnız dosyaya yazılır; üst klasör önceden
oluşturulmuş olmalıdır.

| Çıkış kodu | Anlamı |
| --- | --- |
| 0 | Zorunlu kontroller geçti; uyarı bulunabilir |
| 1 | Kalite, araç, çözme, ölçüm veya rapor yazma hatası |
| 2 | Geçersiz komut veya profil |

Analiz hataları seçilen rapor biçiminde başarısız bir `analysis` kontrolü olarak
gösterilir. Uyarılar çıkış kodunu değiştirmez. JUnit çıktısında uyarılar
`system-out`, başarısız kontroller `failure` öğesiyle gösterilir.

## Profiller

Hazır profiller içerik üretimi için başlangıç kurallarıdır; platformların güncel
yükleme sınırlarını veya videonun kabul edileceğini garanti etmez.

| Profil | Görüntü boyutu | Oran | Ortalama fps | Süre |
| --- | --- | --- | --- | --- |
| `shorts` | 1080×1920 | 9:16 | 24–60 | 0,1–60 saniye |
| `reels` | 1080×1920 | 9:16 | 24–60 | 0,1–90 saniye |
| `tiktok` | 1080×1920 | 9:16 | 24–60 | 0,1–180 saniye |

Ortak eşikler: en fazla 1,5 saniye donma, 0,5 saniye siyah görüntü ve 2 saniye
sessizlik. Ses akışı zorunludur. Hedef ses yüksekliği −14 LUFS, tolerans ±2 LUFS'tır;
bu sınırın dışı varsayılan olarak uyarıdır. Örnek tepe değeri −0,1 dBFS veya
gerçek tepe değeri −0,1 dBTP üzerine çıkarsa kontrol başarısız olur.

Süre eşikleri toplam süreye değil, en uzun kesintisiz bölüme uygulanır; baştaki
ve sondaki bölümler de sayılır. Eşiğe eşit değer geçer. Siyah görüntü ve sessizlikte
algılama alt sınırı 1 ms'dir. Normal kare aralıklarını donma saymamak için donma
filtresi en az bir ortalama kare süresi artı 1 ms bekler; çok kısa tekrarlar
kaçabilir. Hassasiyet kare ve örnek süresiyle sınırlıdır. Tam dijital sessizlikte ölçülen
`-inf` değeri JSON'da `"-inf"` metniyle gösterilir. Sessiz video sessizlik
kontrolünden kalır.

Özel TOML/JSON dosyaları düz bir tablo/nesne olmalıdır. `extends` ile bir hazır
profilden başlanır; verilmezse `shorts` kullanılır. Eksik alanlar devralınır;
bilinmeyen alan, yanlış tür, sonlu olmayan sayı ve çelişen sınırlar reddedilir.
Komut satırındaki eşikler profil değerlerini geçersiz kılar.

```toml
extends = "shorts"
name = "benim-kontrolum"
max_duration = 75
max_freeze = 0.5
target_lufs = -14
lufs_tolerance = 2
loudness_severity = "fail"
```

Çözünürlük için `width`/`height`, oran için `aspect_ratio` (sayısal en/boy),
mutlak oran toleransı için `aspect_tolerance` (0.01), fps için `min_fps`/`max_fps`,
süre için `min_duration`/`max_duration` kullanılır. Diğer alanlar `max_black`,
`max_silence`, `silence_db` (−50), `freeze_noise_db` (−60), `black_pixel_threshold`
(0.1), `black_picture_ratio` (0.98), `max_peak_dbfs` ve `require_audio` alanlarıdır.
`loudness_severity`, `warn` veya `fail` olabilir.
[TOML](examples/custom.toml) ve [JSON](examples/custom.json) örnekleri depodadır.

## Çalışma biçimi ve sınırlar

Akış bilgileri ffprobe JSON çıktısından alınır. FFmpeg videoyu ve sesi iki ayrı
geçişte çözer. Örnek tepe değeri loudnorm'dan önce ölçülür; rapor normalleştirilmiş
çıktıyı değil özgün girdinin ölçümlerini kullanır. Çıktı diske video olarak yazılmaz.
Araç hatası veya gerekli ses ölçümünün eksikliği kontrolü başarısız yapar.
`--timeout` her alt işlem için ayrı uygulanır; varsayılan 300 saniyedir.

Kapak görseli dışındaki ilk video ve ilk ses akışı kontrol edilir. Birden fazla
akış varsa uyarı verilir. Dik açılı dönüş ve piksel oranı görüntü oranı hesabına
katılır. Ortalama fps kontrol edilir; değişken fps ve tek tek kare zamanlarının
sürekliliği doğrulanmaz. Akış süresi yoksa kapsayıcı süresi kullanılır; bu durumda
sesin tam olarak ne kadar alanı kapladığı bilinmeyebilir. Video, sesten
`max_silence` değerinden uzun sürerse `audio_coverage` başarısız olur.
Akış başlangıç farkları karşılaştırılmaz; olay zamanları ilgili akışın başına göredir.

Sabit başlık kartları, kararmalar ve bilinçli duraklamalar uyarılabilir; eşikleri
içeriğinize göre ayarlayın. Tam ölçeğe yakın ses tepeleri kırpılma riskini gösterir,
önceden kırpılma yaşandığını kesin kanıtlamaz. Konuşma tanıma, algısal kalite
değerlendirmesi, kodek politikası veya platform API doğrulaması yapılmaz.
Filtrelerin davranışı için [FFmpeg belgelerine](https://ffmpeg.org/ffmpeg-filters.html) bakın.

## Geliştirme

```console
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m ruff check src tests
python -m ruff format --check src tests
python -m build
```

Kurulum yapmadan test etmek için `PYTHONPATH=src` ayarlayın
(PowerShell: `$env:PYTHONPATH='src'`). Testler standart kütüphanedeki `unittest` ile
çalışır. FFmpeg varsa küçük `testsrc` + `sine` videoları üretilir; temiz video,
donmuş/siyah/sessiz görüntü ve kırpılmış ses kontrol edilir. FFmpeg yoksa bu testler
atlanır; uçtan uca test ayrıca PATH üzerinde ffprobe gerektirir.
`VIDEO_QA_TEST_FFMPEG` ile test ikilisini seçebilirsiniz. Geçici test dosyaları
git tarafından izlenmeyen `is/tests/` altında tutulur.

CI; Ubuntu ve Windows üzerinde Python 3.10 ve 3.14 ile lint, biçim, test ve paket
derleme kontrollerini çalıştırır. Her iki FFmpeg aracı da CI ortamına kurulur.

## Lisans

MIT. Copyright (c) 2026 Yusuf Berat Zengin.
