# commands.py

PRE_COMMANDS_RESULTS = [
    ("atws", "ELM327", True),
    ("ate0", "OK>", True),
    ("ats0", "OK>", False),
    ("ath0", "OK>", False),
    ("atl0", "OK>", False),
    ("atal", "OK>", False),
    ("atcaf0", "OK>", False),
    ("atcfc1", "OK>", False),
    ("AT SH 7E4", "OK>", False),
    ("AT FC SH 7E4", "OK>", False),
    ("AT FC SD 30 00 00", "OK>", False),
    ("AT FC SM 1", "OK>", False),
    ("AT ST FF", "OK>", False),
    ("AT AT 0", "OK>", False),
    ("AT SP 6", "OK>", False),
    ("AT AT 1", "OK>", False),
    ("AT CRA 7EC", "OK>", False)
    # ("AT FC SH 7e4", "OK>", False),
]

COMMANDS_RESULTS = [
    ("03 222002", "05622002", True, "Soc"),
    ("03 22320C", "0562320C", True, "Energy"),
    ("03 223451", "05623451", True, "Range"),
    ("03222006", "22006", True, "Odometer"),
    ("03 22 320C", "", True)
]
