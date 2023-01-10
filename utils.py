from sunday.core.getException import getException

HaodfError = getException({
    10001: '城市输入错误',
    })

code2name_province_map = {
        '31': 'shanghai',
        '33': 'zhejiang',
        '13': 'hebei',
        }
def code2name_province(code):
    if code is None: code = '31'
    code = str(code)
    if code not in code2name_province_map and code not in code2name_province_map.values():
        raise HaodfError(10001)
    return code2name_province_map.get(code) or code
