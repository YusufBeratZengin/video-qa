# video-qa

[![CI](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/video-qa.svg)](https://pypi.org/project/video-qa/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

FFmpeg kullanarak render edilmiş videolar için yerel kalite kontrol kapısı.

Yayınlamadan önce veya otomatik bir CI denetimi olarak donmuş kareleri, siyah bölümleri,
eksik veya sessiz sesi, kırpılma riski taşıyan ses tepelerini, ses yüksekliği sapmalarını
ve beklenmeyen çözünürlük/fps/süre durumlarını tespit eder. Remotion render'ları veya
FFmpeg otomasyon betikleri sonrası kullanım için idealdir.

[English](README.md) · [Katkı rehberi](CONTRIBUTING.md) · [Değişiklikler](CHANGELOG.md)

![video-qa terminal demosu](docs/demo.svg)

## Neden video-qa?

* **%100 Yerel ve Sıfır Bulut Maliyeti**: FFmpeg ile doğrudan kendi makinenizde veya CI sunucunuzda çalışır. Video yükleme, üçüncü taraf API çağrısı ve abonelik ücreti yoktur.
* **Eşzamanlı Otomatik Kusur Tespiti**: Donmuş kareleri, siyah ekranları, sessiz ses kopmalarını, tepe kırpılmalarını, ses yüksekliği sapmalarını ve ses/görüntü uyumsuzluklarını izleyicileriniz fark etmeden önce tespit eder.
* **CI/CD ve Remotion Boru Hatları İçin Tasarlandı**: Yerel JUnit XML, katı JSON çıktısı, standart çıkış kodları ve YouTube Shorts, Instagram Reels, TikTok hazır profilleriyle GitHub Actions'a doğrudan bağlanır.

## Hızlı başlangıç

Python 3.10+ ve yerel bir FFmpeg kurulumu gerektirir.

```console
# 1. video-qa paketini kurun (PATH üzerinde ffmpeg yoksa '.[ffmpeg]' ekleyin)
python -m pip install .

# 2. Render edilen videonuzu yerleşik Shorts profiliyle denetleyin
video-qa check out.mp4 --profile shorts
```

PATH üzerinde `ffprobe` varsa veya `--ffprobe` ile belirtilmişse metaveriler ffprobe JSON ile okunur. `ffprobe` bulunmadığında `video-qa` otomatik olarak yerleşik `ffmpeg -hide_banner -i` çözümleyicisine geçer; böylece harici ffprobe bağımlılığı olmadan tam işlevsellikle çalışır.

## Kullanım örnekleri

```console
# Yerleşik profilleri ve eşik değerlerini listeleme
video-qa --list-profiles

# Özel eşik değerleri belirterek çalıştırma
video-qa check out.mp4 --profile shorts --max-freeze 1.5 --target-lufs -14
video-qa check out.mp4 --profile reels --max-duration 120 --max-silence 1

# Makine tarafından okunabilir JSON veya JUnit XML raporu alma
video-qa check out.mp4 --profile tiktok --format json --output report.json
video-qa check out.mp4 --profile examples/custom.toml --format junit --output junit.xml

# Uyarı durumunda CI sürecini durdurma (çıkış kodu 1)
video-qa check out.mp4 --fail-on-warn

# Özel zaman aşımı ve ikili yolları
video-qa check out.mp4 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe --timeout 600
```

### Komut Satırı Seçenekleri

* `--profile`: Hazır profil adı (`shorts`, `reels`, `tiktok`) veya özel `.toml`/`.json` dosya yolu.
* `--list-profiles`: Yerleşik profilleri ve varsayılan eşiklerini yazdırıp çıkar.
* `--fail-on-warn`: Uyarıları (örneğin ses yüksekliği sapmalarını) başarısızlık sayar (çıkış kodu 1).
* `--format`: Rapor biçimi: `human` (varsayılan tablo), `json` (katı şema) veya `junit` (JUnit XML).
* `--output`: Raporu stdout yerine doğrudan belirtilen dosyaya yazar.
* `--timeout`: Alt işlem başına saniye cinsinden zaman aşımı (varsayılan: 300).
* `--ffmpeg` / `--ffprobe`: Özel çalıştırılabilir dosya yolları.

| Çıkış kodu | Anlamı |
| --- | --- |
| 0 | Tüm zorunlu kontroller geçti; uyarılar bulunabilir (`--fail-on-warn` verilmedikçe) |
| 1 | Kalite başarısızlığı, çözme/araç/ölçüm hatası, `--fail-on-warn` ile uyarı veya rapor yazma hatası |
| 2 | Geçersiz bağımsız değişkenler veya profil yapılandırması |

### CI/CD Entegrasyonu (GitHub Actions)

Remotion veya FFmpeg ile video render ettikten sonra CI hattınızda `video-qa`'yı otomatik kalite kapısı olarak çalıştırabilirsiniz. Tam ve yeniden kullanılabilir bir iş akışı için [examples/github-workflow.yml](examples/github-workflow.yml) dosyasına bakın.

```yaml
- name: video-qa kalite kapısını çalıştır
  run: video-qa check out.mp4 --profile shorts --format junit --output junit.xml

- name: JUnit raporunu yükle
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: video-qa-junit-report
    path: junit.xml
```

### Örnek Raporlar

#### Konsol tablosu (`--format human`)

```text
out.mp4 (profile: shorts, probe: ffmpeg)
STATUS  CHECK           DETAIL
PASS    resolution      Display raster 1080x1920; expected 1080x1920
PASS    aspect_ratio    Display aspect 0.56250; expected 0.56250
PASS    fps             Average 30.000 fps; allowed 24-60
PASS    duration        3.000s; allowed 0.1-60s
PASS    freeze          Longest 0.000s across 0 event(s); allowed <= 1.5s
PASS    black           Longest 0.000s across 0 event(s); allowed <= 0.5s
PASS    silence         Longest 0.000s across 0 event(s); allowed <= 2s
PASS    audio           Audio stream present
PASS    clipping        Sample peak -17.687953 dBFS; allowed <= -0.1 dBFS
PASS    true_peak       True peak -17.69 dBTP; allowed <= -0.1 dBTP
WARN    loudness        Integrated -21.8 LUFS; target -14 +/- 2
PASS    audio_coverage  Video extends 0.000s beyond audio; allowed <= 2s
PASS: 0 failure(s), 1 warning(s)
```

#### JUnit XML raporu (`--format junit`)

```xml
<?xml version='1.0' encoding='utf-8'?>
<testsuite name="video-qa" tests="12" failures="0" errors="0" skipped="0">
  <properties>
    <property name="input" value="out.mp4" />
    <property name="profile" value="shorts" />
    <property name="probe_source" value="ffmpeg" />
    <property name="warnings" value="1" />
  </properties>
  <testcase classname="video_qa" name="resolution" />
  <testcase classname="video_qa" name="aspect_ratio" />
  <testcase classname="video_qa" name="fps" />
  <testcase classname="video_qa" name="duration" />
  <testcase classname="video_qa" name="freeze" />
  <testcase classname="video_qa" name="black" />
  <testcase classname="video_qa" name="silence" />
  <testcase classname="video_qa" name="audio" />
  <testcase classname="video_qa" name="clipping" />
  <testcase classname="video_qa" name="true_peak" />
  <testcase classname="video_qa" name="loudness">
    <system-out>WARNING: Integrated -21.8 LUFS; target -14 +/- 2</system-out>
  </testcase>
  <testcase classname="video_qa" name="audio_coverage" />
</testsuite>
```

Örnek çıktı dosyaları: [examples/report.json](examples/report.json) ve [examples/junit.xml](examples/junit.xml).

## Yapılandırma

Yerleşik profiller popüler kısa video platformları için temel standartları sunar:

| Profil | Görüntü matrisi | En-boy oranı | Ortalama fps | Süre |
| --- | --- | --- | --- | --- |
| `shorts` | 1080×1920 | 9:16 | 24–60 | 0.1–60 saniye |
| `reels` | 1080×1920 | 9:16 | 24–60 | 0.1–90 saniye |
| `tiktok` | 1080×1920 | 9:16 | 24–60 | 0.1–180 saniye |

### Varsayılan Eşikler

| Ayar | Varsayılan | Aşıldığında Sonuç |
| --- | --- | --- |
| `max_freeze` | 1.5 saniye | Başarısızlık (Failure) |
| `max_black` | 0.5 saniye | Başarısızlık (Failure) |
| `max_silence` | 2 saniye | Başarısızlık (Failure) |
| `target_lufs` / `lufs_tolerance` | −14 / ±2 LUFS | Uyarı (Warning) |
| `max_peak_dbfs` | −0.1 dBFS örnek tepe ve −0.1 dBTP gerçek tepe | Başarısızlık (Failure) |
| `require_audio` | `true` | Ses akışı yoksa başarısızlık |

### Özel Profiller (TOML ve JSON)

Özel profil dosyaları `extends` anahtarıyla yerleşik bir profili miras alabilir (varsayılan `shorts`):

```toml
extends = "shorts"
name = "my-render-gate"
max_duration = 75
max_freeze = 0.5
target_lufs = -14
lufs_tolerance = 2
loudness_severity = "fail"
```

Yapılandırılabilir anahtarlar: `width`, `height`, `aspect_ratio`, `aspect_tolerance`, `min_fps`, `max_fps`, `min_duration`, `max_duration`, `max_freeze`, `max_black`, `max_silence`, `silence_db` (−50 dB), `freeze_noise_db` (−60 dB), `black_pixel_threshold` (0.1), `black_picture_ratio` (0.98), `max_peak_dbfs`, `require_audio` ve `loudness_severity` (`warn` veya `fail`). Örnekler: [TOML](examples/custom.toml) ve [JSON](examples/custom.json).

## SSS ve Sınırlar

* **Çözme ve analiz nasıl çalışır?**
  Akış metaverileri `ffprobe` (veya `ffmpeg -i` yedeği) ile alınır. Analiz eşzamanlı iki FFmpeg iş parçacığıyla yürütülür: video akışında `freezedetect`/`blackdetect`, ses akışında `silencedetect`/`astats`/`loudnorm`. Modern çok çekirdekli sistemlerde 60 saniyelik video yaklaşık 2.7 saniyede (~22 kat gerçek zamanlı hızda) taranır.
* **Hareketsiz başlık kartları veya sanatsal duraklamalar tetiklenebilir mi?**
  Evet. Kasıtlı duraklamalar, sabit görsel slaytlar veya ses açılma/kapanma efektleri belirlenen süreleri aşarsa donma ya da sessizlik olarak işaretlenebilir. İhtiyacınıza göre `--max-freeze`, `--max-black` veya `--max-silence` eşiklerini esnetebilirsiniz.
* **Ses tepeleri ve ses yüksekliği nasıl ölçülür?**
  Örnek tepe (sample peak) ve gerçek tepe (true peak) değerleri orijinal ham ses üzerinden ölçülür. Ses yüksekliği EBU R128 entegre standardına (LUFS) göre ölçülür. Tamamen sessiz ses `-inf` döner (JSON çıktısında `"-inf"` metni olarak serileştirilir).
* **Kapsam dışı durumlar nelerdir?**
  `video-qa` ses tanıma (STT), algısal sübjektif video kalitesi puanlaması (VMAF gibi), codec uyumluluk denetimi veya platform API yükleme doğrulaması yapmaz.
* **Medya dosyalarım herhangi bir yere yükleniyor mu?**
  Hayır. Tüm analiz tamamen yerel bilgisayarınızda veya CI sunucunuzda gerçekleşir. FFmpeg çağrılarında ağ protokolleri kapalıdır. Oluşturulan raporlar yerel dosya yollarını ve çözücü hata iletilerini içerebilir; paylaşmadan önce inceleyiniz.

## Katkıda bulunma

Katkılarınızı memnuniyetle kabul ediyoruz! Lütfen [CONTRIBUTING.md](CONTRIBUTING.md) rehberimizi ve [Davranış Kuralları](CODE_OF_CONDUCT.md)'nı inceleyin.

### Yerel Geliştirme Kurulumu

```console
# Depoyu klonlayın ve geliştirme bağımlılıklarıyla düzenlenebilir modda kurun
git clone https://github.com/YusufBeratZengin/video-qa.git
cd video-qa
python -m pip install -e ".[dev]"

# Testleri ve kapsam raporunu çalıştırın
python -m pytest

# Kod stili ve biçimlendirme kontrolleri
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts

# Statik tip kontrolü
python -m mypy

# Paket dağıtımlarını derleyin
python -m build
```

## Lisans

MIT. Telif hakkı (c) 2026 Yusuf Berat Zengin. Ayrıntılar için [LICENSE](LICENSE) dosyasına bakınız.
