
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

- Beacon, `255.255.255.255:<beacon_udp_port>` adresine broadcast edilir.

## RS Test Durum Kodları

- `0`: Boş/idle
- `1`: Test isteği
- `2`: Test devam ediyor
- `3`: Test başarılı
- `-1`: Test hatalı 

## Modbus Alan Tipi

Bu simülatörde kullanılan register tipleri **Holding Register (4x)** tipindedir.
- Okuma için: Function Code **03 (Read Holding Registers)**
- Yazma için: Function Code **06 (Write Single Register)** veya **16 (Write Multiple Registers)**

Coils (0x), Discrete Inputs (1x) ve Input Registers (3x) bu senaryo için kullanılmaz.

