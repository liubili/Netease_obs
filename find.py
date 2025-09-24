# ida_scan_mov_rcx.py
# 用法: 在 IDA Python 控制台运行
# 扫描当前函数中 mov [reg+offset], rcx 指令，并尝试回溯 reg 来源

import idaapi
import idautils
import idc

def is_mov_reg_mem(op):
    """检查指令是否 mov [reg+offset], rcx"""
    if op is None:
        return False
    mnem = idc.print_insn_mnem(op)
    if mnem != "mov":
        return False
    # op1 是内存访问，op2 是 rcx
    op1_type = idc.get_operand_type(op, 0)
    op2_type = idc.get_operand_type(op, 1)
    if op1_type == idc.o_displ and op2_type == idc.o_reg:
        if idc.print_operand(op, 1) == "rcx":
            return True
    return False

def backtrace_reg(ea, reg_name, max_back=20):
    """简单回溯寄存器来源"""
    for i in range(max_back):
        ea = idc.prev_head(ea)
        if ea == idc.BADADDR:
            break
        mnem = idc.print_insn_mnem(ea)
        if mnem == "mov":
            dst = idc.print_operand(ea, 0)
            src = idc.print_operand(ea, 1)
            if dst == reg_name:
                return ea, src
    return None, None

def scan_func(ea):
    """扫描函数内 mov [reg+offset], rcx"""
    func = idaapi.get_func(ea)
    if not func:
        print(f"无法找到函数 at {hex(ea)}")
        return
    start = func.start_ea
    end = func.end_ea
    print(f"扫描函数 {hex(start)} - {hex(end)}")
    
    for head in idautils.Heads(start, end):
        if is_mov_reg_mem(head):
            op1 = idc.print_operand(head, 0)
            print(f"找到 mov 指令 at {hex(head)}: {op1} <- rcx")
            base_reg = op1.split('+')[0].strip('[]')
            back_ea, src = backtrace_reg(head, base_reg)
            if back_ea:
                print(f"  {base_reg} 来源于 {src} at {hex(back_ea)}")
            else:
                print(f"  {base_reg} 来源未找到 (可能是参数或全局)")

# 使用示例: 将光标放在函数内部，然后运行
scan_func(idc.here())
