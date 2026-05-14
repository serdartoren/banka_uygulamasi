# RS8 Modbus TCP Simülatörü

Bu proje, **8 adet RS çıkışı olan bir cihazın otomasyon test simülasyonu** için hazırlanmıştır.
Gerçek RS haberleşme katmanı yoktur; yalnızca Modbus register davranışı ve çıkış test akışını simüle eder.

## Özellikler

- Modbus TCP server olarak çalışır.
- Toplam **10 adet holding register** sunar (okunabilir/yazılabilir).
- Cihaz IP aldıktan sonra UDP broadcast ile beacon mesajı yayınlar:
  - `name=<cihaz_adi>;ip=<ip>;port=<modbus_port>`
- 8 çıkışın toplu testi ve tek tek testleri register tetikleyicileri ile yönetilir.

## Kurulum

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Çalıştırma

```bash
python simulator.py --name RS8-SIM --modbus-port 5020 --beacon-udp-port 37020
```

Opsiyonel parametreler:

- `--beacon-interval`: Beacon gönderim aralığı (sn), varsayılan `2.0`
- `--test-step-delay`: Test sırasında kanal adımları arası bekleme (sn), varsayılan `0.5`

## Register Haritası (Enum Açıklamaları)

Aşağıdaki tüm register'lar Holding Register (4x) olup hem okunabilir hem yazılabilirdir.

> Not: `pymodbus` 3.x sürümlerinde datastore başlangıç adresi teknik olarak 1 tabanlıdır.
> Bu simülatörde kullanıcıya görünen register ofsetleri yine **0..9** olarak korunmuştur.

```text
0  -> REG_ALL_TEST
1  -> REG_CLEAR_ALL
2  -> REG_RS1_TEST
3  -> REG_RS2_TEST
4  -> REG_RS3_TEST
5  -> REG_RS4_TEST
6  -> REG_RS5_TEST
7  -> REG_RS6_TEST
8  -> REG_RS7_TEST
9  -> REG_RS8_TEST
```

### Enum Anlamları

- `REG_ALL_TEST` (0):
  - `1` yazıldığında 8 çıkış sırayla test edilir.
  - Test bitince register tekrar `0` yapılır.

- `REG_CLEAR_ALL` (1):
  - `1` yazıldığında tüm register'lar `0` yapılır.
  - Simüle edilen çıkış durumları sıfırlanır.

- `REG_RS*_TEST` (2..9):
  - İlgili çıkışı tek başına test eder.
  - Durum akışı aşağıdaki gibidir:
    - `1` = Test isteği (client yazar)
    - `2` = Test çalışıyor
    - `3` = Test başarılı
    - `-1` = Test hatalı (`0xFFFF` olarak okunur)

## Notlar

- Modbus server `0.0.0.0` üzerinde dinler.
- Beacon, `255.255.255.255:<beacon_udp_port>` adresine broadcast edilir.
- Gerçek RS sürücü işlemleri dahil değildir; bu uygulama otomasyon ekipleri için simülasyondur.

## RS Test Durum Kodları

- `0`: Boş/idle
- `1`: Test isteği
- `2`: Test devam ediyor
- `3`: Test başarılı
- `-1`: Test hatalı (Modbus register değerinde `65535` / `0xFFFF`)

## Modbus Alan Tipi

Bu simülatörde kullanılan register tipleri **Holding Register (4x)** tipindedir.
- Okuma için: Function Code **03 (Read Holding Registers)**
- Yazma için: Function Code **06 (Write Single Register)** veya **16 (Write Multiple Registers)**

Coils (0x), Discrete Inputs (1x) ve Input Registers (3x) bu senaryo için kullanılmaz.


## Master Test Client

Simülatörü test etmek için `master_tester.py` dosyası eklendi.

```bash
python master_tester.py --host 127.0.0.1 --port 5020 --unit-id 1
```

Bu istemci sırasıyla:
1. Register'ları okur.
2. `REG_CLEAR_ALL` yazar.
3. `REG_RS1_TEST` için `1 -> 2 -> 3/-1` akışını takip eder.
4. `REG_ALL_TEST` yazar ve tekrar register okur.
- Not: `master_tester.py`, farklı `pymodbus` sürümlerindeki `slave/device_id` parametre farkını otomatik yönetir.
