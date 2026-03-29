from smbus2 import SMBus

found = []
with SMBus(1) as bus:
    for addr in range(0x03, 0x78):
        try:
            bus.write_quick(addr)
            found.append(hex(addr))
        except OSError:
            pass

print("Found I2C devices:", found)