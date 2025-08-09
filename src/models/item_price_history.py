class QuantityEnum:
    ONE = 1
    TEN = 10
    HUNDRED = 100
    THOUSAND = 1000


# ItemPriceHistory
# id integer pk
# gid integer not null
# quantity: QuantityEnum not null
# price: integer > 0 not null
# recorded_at datetime not null
# server_id integer not null
