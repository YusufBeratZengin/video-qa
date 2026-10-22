# video-qa

[![CI](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml/badge.svg)](https://github.com/YusufBeratZengin/video-qa/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Yayınlamadan önce render edilmiş videolara yerel kalite kontrolü uygular.
Donmuş görüntü, siyah bölümler, eksik veya sessiz ses, kırpılma riski taşıyan
ses tepeleri, ses yüksekliği ve çözünürlük/fps/süre sapmalarını kontrol eder.
Remotion veya FFmpeg ile video üreten iş akışlarında CI kontrolü olarak kullanılabilir.

[English](README.md) · [Katkı rehberi](CONTRIBUTING.md) · [Değişiklikler](CHANGELOG.md)

## Kurulum

Python 3.10 veya üzeri ve yerel bir FFmpeg kurulumu gerekir. PATH üzerinde `ffprobe`
bulunuyorsa veya `--ffprobe` ile belirtilmişse kapsayıcı ve akış bilgileri ffprobe
ile alınır. Sistemde `ffprobe` yoksa `video-qa` otomatik olarak `ffmpeg -hide_banner -i`
çıktısını ayrıştırmaya geçer; böylece ek bir ffprobe ikilisi kurmadan doğrudan FFmpeg
ile çalışabilir.

FFmpeg dağıtımınız `freezedetect`, `blackdetect`, `silencedetect`, `astats` ve
`loudnorm` filtrelerini içermelidir.
[FFmpeg indirme sayfasından](https://ffmpeg.org/download.html) uygun dağıtımı seçebilirsiniz.

Depo klasöründe:

```console
python -m pip install .
video-qa check out.mp4 --profile shorts
```

`python -m pip install '.[ffmpeg]'`, PATH üzerinde FFmpeg yoksa `imageio-ffmpeg`
paketinin ikilisini kullanmayı sağlar. `imageio-ffmpeg` yalnızca `ffmpeg` ikilisi
sağlasa da `video-qa` yerleşik FFmpeg metaveri yedeği sayesinde sorunsuz çalışır.
İkili yollarını `--ffmpeg` ve `--ffprobe` ile doğrudan da verebilirsiniz:

```console
video-qa check out.mp4 --ffmpeg /path/to/ffmpeg --ffprobe /path/to/ffprobe
```

İşlem bilgisayarınızda çalışır; video yüklenmez, API çağrılmaz, çalışma sırasında
ikili indirilmez ve kaynak video değiştirilmez. FFmpeg girdilerinde ağ protokolleri
kapalıdır. Raporlar dosya yolunu ve bazen çözücü hata mesajlarını içerir;
paylaşmadan önce gözden geçirin.

## Kullanım

```console
video-qa --list-profiles
video-qa check out.mp4 --profile shorts --max-freeze 1.5 --target-lufs -14
video-qa check out.mp4 --profile reels --max-duration 120 --max-silence 1
video-qa check out.mp4 --profile tiktok --format json --output report.json
video-qa check out.mp4 --profile examples/custom.toml --format junit --output junit.xml
video-qa check out.mp4 --fail-on-warn
python -m video_qa check out.mp4 --max-black 0.25 --timeout 600
```

Komut satırı seçenekleri:
* `--list-profiles`: Yerleşik profilleri ve eşik değerlerini yazdırıp çıkar.
* `--fail-on-warn`: Uyarıları (örneğin ses yüksekliği sapmaları veya çoklu akış bildirimleri) başarısızlık sayar (çıkış kodu 1).
* `--format`: Çıktı biçimi (`human` tablo, `json` katı JSON, `junit` JUnit XML).
* `--output`: Raporu stdout yerine doğrudan belirtilen dosyaya yazar.

| Çıkış kodu | Anlamı |
| --- | --- |
| 0 | Zorunlu kontroller geçti; uyarı bulunabilir (`--fail-on-warn` verilmedikçe) |
| 1 | Kalite, araç, çözme, ölçüm, uyarı (`--fail-on-warn` ile) veya rapor yazma hatası |
| 2 | Geçersiz komut, seçenek veya profil yapılandırması |

Analiz hataları seçilen rapor biçiminde başarısız bir `analysis` kontrolü olarak
gösterilir. Uyarılar varsayılan olarak çıkış kodunu değiştirmez. JUnit çıktısında uyarılar
`system-out`, başarısız kontroller `failure` öğesiyle gösterilir.

## Örnek çıktı

### Konsol tablosu (`--format human`)

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

### JUnit XML raporu (`--format junit`)

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

`scripts/make_examples.py` betiğiyle üretilen tam örnek dosyalar
[examples/report.json](examples/report.json) ve [examples/junit.xml](examples/junit.xml)
altındadır.

## Sürekli Entegrasyon (GitHub Actions)

Remotion veya FFmpeg ile video render ettikten sonra `video-qa` aracını CI hattınızda
otomatik kalite kapısı olarak çalıştırabilirsiniz. Tam örnek iş akışı için
[examples/github-workflow.yml](examples/github-workflow.yml) dosyasına bakın.

```yaml
- name: Run video-qa quality gate
  run: video-qa check out.mp4 --profile shorts --format junit --output junit.xml

- name: Upload JUnit report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: video-qa-junit-report
    path: junit.xml
```

## Profiller ve eşik değerleri

Hazır profiller içerik üretimi için başlangıç kurallarıdır; platformların güncel
yükleme sınırlarını veya videonun kabul edileceğini garanti etmez. Profil listesini
istediğiniz an `video-qa --list-profiles` ile görüntüleyebilirsiniz.

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

## Çalışma biçimi, performans ve sınırlar

Akış metaverileri `ffprobe` JSON çıktısından veya `ffmpeg -hide_banner -i` stderr
çıktısından alınır. Çözme işlemi iş parçacığı havuzuyla iki paralel FFmpeg geçişinde
gerçekleştirilir: görüntüde `freezedetect`/`blackdetect`, seste `silencedetect`/`astats`/`loudnorm`.
İki geçişin eşzamanlı çalışması çok çekirdekli sistemlerde işlem hızını en üst düzeye
çıkarırken her alt işlem için bağımsız `--timeout` güvencesini ve deterministik rapor
sırasını korur. Modern donanımda 60 saniyelik 1080×1920 sentetik bir klibin tam
analizi yaklaşık 2,7 saniye sürer (gerçek zamandan ~22 kat daha hızlı).

Örnek tepe değeri loudnorm'dan önce ölçülür; rapor normalleştirilmiş çıktıyı değil
özgün girdinin ölçümlerini kullanır. Çıktı diske video olarak yazılmaz. Araç hatası
veya gerekli ses ölçümünün eksikliği kontrolü başarısız yapar. `--timeout` her alt işlem
için ayrı uygulanır; varsayılan 300 saniyedir.

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
python -m mypy
python -m build && python -m twine check dist/*
```

Kurulum yapmadan test etmek için `PYTHONPATH=src` ayarlayın
(PowerShell: `$env:PYTHONPATH='src'`). Testler standart kütüphanedeki `unittest` ile
çalışır. FFmpeg varsa küçük `testsrc` + `sine` videoları üretilir; temiz video,
donmuş/siyah/sessiz görüntü ve kırpılmış ses kontrol edilir. FFmpeg yoksa bu testler
atlanır. `VIDEO_QA_TEST_FFMPEG` ile test ikilisini seçebilirsiniz. Geçici test dosyaları
git tarafından izlenmeyen `is/tests/` altında tutulur.

CI; Ubuntu ve Windows üzerinde Python 3.10 ve 3.14 ile lint, biçim, `mypy` tip denetimi,
test ve paket derleme kontrollerini çalıştırır.

## Lisans

MIT. Copyright (c) 2026 Yusuf Berat Zengin.
