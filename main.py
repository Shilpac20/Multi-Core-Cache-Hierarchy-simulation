import math
import os
from cache import Cache
from collections import defaultdict

os.chdir(os.path.dirname(os.path.abspath(__file__)))
filesRequired = ['Traces/addr_prog4','Traces/addr_prog3','Traces/addr_prog2','Traces/addr_prog1']


for filename in filesRequired:
    l1bankQ = [[] for _ in range(8)]  # [Message, Address, source core id,number of inv ack expected]
    homeQ = [[] for _ in range(8)]  # [Message, Address, source core id]
    outstanding_msgQ = [defaultdict(list) for _ in range(8)]  # for the outstanding messages so that repeated mssg is not sent
    outstanding_reqQ = [set() for _ in range(8)]  # for the outstanding block request to L2 so that same block isn't requested twice
    nakQ = [[] for _ in range(8)]
    buffer = [[] for _ in range(8)]
    matQ_buffer = [[] for _ in range(8)]
    old_cores = []

    L1 = [Cache(32768, 8, 64) for _ in range(8)]
    L2 = Cache(4194304, 16, 64)
    L1_readmisscount = [0 for _ in range(8)]
    L1_writemisscount = [0 for _ in range(8)]
    L1_upgrademisscount = [0 for _ in range(8)]
    L1hitcount = [0 for _ in range(8)]
    L2misscount = 0
    L2hitcount = 0
    L1msgcounts = defaultdict(int)
    L2msgcounts = defaultdict(int)
    for i in range(8):
        L1msgcounts[i]=defaultdict(int)

    globalcount = 0
    cycle = 0
    nakcounter = 5

    with open(filename) as f:
        while (True):
            cycle += 1
            
            new_cores = old_cores.copy()
            coresfound = set()
            for i in new_cores:
                coresfound.add(i[0])

            for _ in range(8):
                line = f.readline()
                tmp = line.split()
                
                if len(tmp) < 4:
                    break
            
                if int(tmp[0]) not in coresfound:
                    new_cores.append([int(tmp[0]),tmp[1],int(tmp[2])])
                    coresfound.add(int(tmp[0]))
                else:
                    old_cores.clear()
                    old_cores.append([int(tmp[0]),tmp[1],int(tmp[2])])
                    break
            
            Qempty = True
            if line == '':
                break

            for coreid in range(8):  # l1bank queue
                if len(l1bankQ[coreid]) > 0:
                    Qempty = False

                    message_type = l1bankQ[coreid][0][0]
                    addr = l1bankQ[coreid][0][1]
                    sourceid = l1bankQ[coreid][0][2]
                    blkno = L1[coreid].get_blockno(addr)
                    ack_count = l1bankQ[coreid][0][3]
                    L1msgcounts[coreid][message_type] += 1

                    if (message_type == 'PUTX' and ack_count == 0) or message_type == 'PUTE' or message_type == 'PUT':

                        evicted_blkAddr, evicted_state, bitvector = L1[coreid].Replacement(addr, 1)

                        if evicted_blkAddr is not None:
                            l2state, bitvector, flag = L2.CheckMiss(evicted_blkAddr)
                            if l2state == 'I':
                                pass

                            L2.change_bitvector_replacement(evicted_blkAddr, coreid)
                            if evicted_state == 'M':  # If dirty block is evicted from L1, WB to L2
                                homeQ[sourceid].append(['WB', evicted_blkAddr, L2.find_bank_id(addr)])

                    for j in range(len(buffer[coreid])):
                        if (buffer[coreid][j][0] == 'PUTX' and buffer[coreid][j][2] == 0):
                            evicted_blkAddr, evicted_state, bitvector = L1[coreid].Replacement(buffer[coreid][j][1], 1)
                            L1[coreid].modify_state(addr, 'M')
                            if evicted_blkAddr is not None:
                                L2.change_bitvector_replacement(evicted_blkAddr, coreid)

                                if evicted_state == 'M':  # If dirty block is evicted from L1, WB to L2
                                    homeQ[sourceid].append(
                                        ['WB', evicted_blkAddr, L2.find_bank_id(buffer[coreid][j][1])])
                            break

                    if message_type == 'PUTX' or message_type == 'UPGRADE_ACK':
                        L1[coreid].modify_state(addr, 'M')
                        if message_type == 'PUTX' and ack_count > 0:
                            flag = True
                            for j in range(len(buffer[coreid])):
                                if buffer[coreid][j][1] == addr:
                                    flag = False
                                    break
                            if flag:
                                buffer[coreid].append([message_type, addr, ack_count])
                        if (blkno, 'GETX') in outstanding_reqQ[coreid]:
                            outstanding_reqQ[coreid].remove((blkno, 'GETX'))

                        if (blkno, 'UPGRADE') in outstanding_reqQ[coreid]:
                            outstanding_reqQ[coreid].remove((blkno, 'UPGRADE'))

                        if (blkno, 1) in outstanding_msgQ[coreid]:  # L1 hit for all these messages
                            outstanding_msgQ[coreid].pop((blkno, 1))

                            # L2.modify_bitvector not required as this block already set as owner before serving PUTX

                    elif message_type == 'PUTE':
                        L1[coreid].modify_state(addr, 'E')
                        if (blkno, 'GET') in outstanding_reqQ[coreid]:
                            outstanding_reqQ[coreid].remove((blkno, 'GET'))

                        if (blkno, 0) in outstanding_msgQ[coreid]:  # L1 hit for all these messages
                            outstanding_msgQ[coreid].pop((blkno, 0))

                        if (blkno, 1) in outstanding_msgQ[coreid]:  # L1 hit for all these messages
                            outstanding_msgQ[coreid].pop((blkno, 1))
                            L1[coreid].modify_state(addr, 'M')

                            # L2.modify_bitvector not required as this block already set as owner before serving PUTE


                    elif message_type == 'PUT':
                        L1[coreid].modify_state(addr, 'S')
                        if (blkno, 'GET') in outstanding_reqQ[coreid]:
                            outstanding_reqQ[coreid].remove((blkno, 'GET'))

                        if (blkno, 0) in outstanding_msgQ[coreid]:  # L1 hit for all these messages
                            outstanding_msgQ[coreid].pop((blkno, 0))

                            # L2.modify_bitvector not required as this block already set as sharer before serving PUTE

                        if (blkno, 1) in outstanding_msgQ[coreid]:  # Upgrade for first write req in queue
                            bankid = L2.find_bank_id(outstanding_msgQ[coreid][(blkno, 1)][0][0])
                            homeQ[bankid].append(['UPGRADE', outstanding_msgQ[coreid][(blkno, 1)][0][0], coreid])
                            outstanding_msgQ[coreid].pop((blkno, 1))
                            outstanding_reqQ[coreid].add((blkno, 'UPGRADE'))

                    elif message_type == 'INV':
                        L1[coreid].modify_state(addr, 'I')
                        l1bankQ[sourceid].append(['INVACK', addr, coreid, 0])

                    elif message_type == 'GETX':
                        L1[sourceid].modify_state(addr, 'I')
                        L1[coreid].modify_state(addr, 'M')
                        l1bankQ[coreid].append(['PUTX', addr, sourceid, 0])
                        tmp = l1bankQ[sourceid]
                        L2.modify_bitvector(addr, coreid, 'PDEX')
                        bankid = L2.find_bank_id(addr)
                        homeQ[bankid].append(['ACK', addr, sourceid])

                    # PUTE not possible as E occurs only if S is demanded when no other owner/sharer is present

                    elif message_type == 'GET':
                        L1[coreid].modify_state(addr, 'S')
                        L1[sourceid].modify_state(addr, 'S')
                        l1bankQ[coreid].append(['PUT', addr, sourceid, 0])
                        tmp = l1bankQ[sourceid]

                        L2.modify_bitvector(addr, coreid, 'PSH')
                        L2.modify_bitvector(addr, sourceid, 'PSH')
                        bankid = L2.find_bank_id(addr)
                        homeQ[bankid].append(['SWB', addr, sourceid])


                    elif message_type == 'WB-Req':
                        L1[coreid].modify_state(addr, 'I')
                        bankid = L2.find_bank_id(addr)
                        homeQ[bankid].append(['WB', addr, coreid])

                    elif message_type == 'INVACK':
                        for j in range(len(buffer[coreid])):
                            if (buffer[coreid][j][0] == 'PUTX' and buffer[coreid][j][1] == addr and buffer[coreid][j][
                                2] >= 0):
                                if buffer[coreid][j][2] == 0:
                                    buffer[coreid].pop(j)
                                else:
                                    buffer[coreid][j][2] -= 1

                    l1bankQ[coreid].pop(0)
            for bankid in range(8):
                if len(homeQ[bankid]) > 0:  # [Message, Address, source core id]
                    Qempty = False

                    message_type = homeQ[bankid][0][0]
                    addr = homeQ[bankid][0][1]
                    coreid = homeQ[bankid][0][2]

                    if message_type == 'WB':
                        L2msgcounts[message_type] += 1
               
                    l2state, bitvector, flag = L2.CheckMiss(addr)

                    if not flag and (message_type == 'GETX' and message_type == 'GET' and bitvector[coreid]):
                        pass

                    if flag is False:
                        L2misscount += 1

                        evicted_blkAddr, evicted_state, bitvector = L2.Replacement(addr, 2)  # New blk default 'I' '000000'

                        if evicted_blkAddr is not None and evicted_state != 'I':
                            for i in range(8):
                                if bitvector[i] == '1':
                                    if evicted_state == 'M':  # Gets most up-to-date copy from set bit L1[i] and invalidate it
                                        l1bankQ[i].append(['WB-Req', addr, bankid, 0])  # Give a suitable name to WB-Req
                                        break
                                    L1[i].Evict(evicted_blkAddr)


                    else:
                        L2hitcount += 1

                    if l2state == 'I' and (message_type == 'GET' or message_type == 'GETX'):

                        reply = 'PUTE'
                        if message_type == 'GETX':
                            reply = 'PUTX'

                        L2.modify_bitvector(addr, coreid, 'M')  # directory doesn't know E state
                        l1bankQ[coreid].append([reply, addr, bankid, 0])
                        L2msgcounts[message_type] += 1
                    elif l2state == 'S' and message_type == 'GET':
                        L2.modify_bitvector(addr, coreid, 'S')

                        l1bankQ[coreid].append(['PUT', addr, bankid, 0])
                        L2msgcounts[message_type] += 1
                        
                    elif l2state == 'S' and (message_type == 'GETX' or message_type == 'UPGRADE'):
                        L2msgcounts[message_type] += 1
                        sharers = []
                        for i in range(8):
                            if bitvector[i] == '1':
                                sharers.append(i)
                        

                        if coreid in sharers:
                            l1bankQ[coreid].append(['UPGRADE_ACK', addr, bankid, len(sharers) - 1])
                            L2.modify_bitvector(addr, coreid, 'M')
                            sharers.remove(coreid)

                        else:
                            l1bankQ[coreid].append(['PUTX', addr, bankid, len(sharers)])
                            L2.modify_bitvector(addr, coreid, 'M')
                        for sharecore in sharers:
                            l1bankQ[sharecore].append(['INV', addr, coreid, 0])

                    elif l2state == 'M' and (message_type == 'GET' or message_type == 'GETX'):
                        L2msgcounts[message_type] += 1
                        owner = None
                        for i in range(8):
                            if bitvector[i] == '1':
                                owner = i
                                break
                        
                        l1bankQ[owner].append([message_type, addr, coreid, 0])

                        if message_type == 'GET':
                            L2.modify_state(addr, 'PSH')  # pending shared
                        
                        else:
                            L2.modify_state(addr, 'PDEX')  # pending dirty exclusive
                        
                    elif l2state == 'PSH':
                        if message_type == 'SWB':
                            L2msgcounts[message_type] += 1
                            L2.modify_state(addr, 'S')
                        else:
                            nakQ[coreid].append([addr, nakcounter, message_type])
                            L2msgcounts['NAK'] += 1
                    elif l2state == 'PDEX':
                        if message_type == 'ACK':
                            L2.modify_state(addr, 'M')
                            L2msgcounts[message_type] += 1
                        else:
                            nakQ[coreid].append([addr, nakcounter, message_type])
                            L2msgcounts['NAK'] += 1

                    homeQ[bankid].pop(0)




            
            # Processing of nakQ, matQ_buffer and new_cores to get cores that will be processed this cycle begins
            nak_cores = []
            cores = []
            cores_booked = set()

            for coreid in range(8):
                nakQ[coreid].reverse()  # queue has to be processed in sequence
                for j in nakQ[coreid][::-1]:  # j format: addr, nakcounter, message_type
                                            # queue processed in reverse so that elements can be removed on the go
                    if j[1] == 0:
                        if message_type == 'GETX' or message_type == 'UPGRADE':
                            rw = 'W'
                        else:
                            rw = 'R'

                        cores.append([coreid, rw, j[0]])
                        cores_booked.add(coreid)

                        nakQ[coreid][::-1].remove(j)  # removed after revsre so that actual first occurance is removed
                        break
                    else:
                        j[1] -= 1
                nakQ[coreid].reverse()  # undo effect of previous reverse

            for coreid in range(8):
                if coreid not in cores_booked and len(matQ_buffer[coreid]) > 0:
                    cores.append(matQ_buffer[coreid][0])
                    cores_booked.add(coreid)
                    matQ_buffer[coreid].pop(0)
                    
            for core in new_cores[::-1]:  # doesn't matter if processed in reverse
                if core[0] not in cores_booked:
                    cores.append(core)
                    new_cores.remove(core)
                else:
                    matQ_buffer[core[0]].append(core)
            # Cores that will be processed this cycle ends

            for core in cores:  # cores is a list containing cores to be processed in this cycle, format: [[coreid, R/W, Address],..]
                Qempty = False
                #x += 1
                coreid = core[0]

                if core[1] == 'R':
                    rw = 0
                else:
                    rw = 1
                addr = core[2]
            
                # CACHE ACTION BEGINS!!
                # rw M/E ->hit (modify state to M in case of E)
                # rw S -> upgrade
                # rw I -> GetX
                # not rw S/M/E -> hit
                # not rw I -> Get

                l1state, _, _ = L1[coreid].CheckMiss_L1(addr)
                blkno = L1[coreid].get_blockno(addr)
                flag_pending_hit = False
                if not rw and (blkno, 'GET') in outstanding_reqQ[coreid]:
                    l1state = 'S'
                    flag_pending_hit = True
                elif rw and ((blkno, 'GETX') in outstanding_reqQ[coreid] or (blkno, 'UPGRADE') in outstanding_reqQ[coreid]):
                    l1state = 'M'
                    flag_pending_hit = True
                if (rw and l1state in ['M', 'E']) or (not rw and l1state in ['M', 'S', 'E']):
                    L1hitcount[coreid] += 1
                    if not flag_pending_hit:
                        if rw and l1state == 'E':
                            L1[coreid].modify_state(addr, 'M')
                            l1state = 'M'

                        L2.modify_bitvector(addr, coreid, l1state)  # modify L2 bitvector when L1 hit or when req reaches L2

                else:
                    if l1state == 'I':
                        if rw:
                            L1_writemisscount[coreid] += 1
                        else:
                            L1_readmisscount[coreid] += 1
                    elif l1state == 'S' and rw:
                        L1_upgrademisscount[coreid] += 1

                    blkno = L1[coreid].get_blockno(addr)
                    bankid = L2.find_bank_id(addr)

                    if rw:
                        if l1state == 'S':
                            if (blkno, 'UPGRADE') not in outstanding_reqQ[coreid]:
                                homeQ[bankid].append(['UPGRADE', addr, coreid])
                                outstanding_reqQ[coreid].add((blkno, 'UPGRADE'))

                            else:
                                outstanding_msgQ[coreid][(blkno, rw)].append([addr, coreid])

                        else:
                            if (blkno, 'GET') in outstanding_reqQ[coreid] or (blkno, 'GETX') in outstanding_reqQ[coreid]:
                                outstanding_msgQ[coreid][(blkno, rw)].append([addr, coreid])

                            else:
                                homeQ[bankid].append(['GETX', addr, coreid])
                                outstanding_reqQ[coreid].add((blkno, 'GETX'))

                    else:
                        if (blkno, 'GET') not in outstanding_reqQ[coreid]:
                            homeQ[bankid].append(['GET', addr, coreid])
                            outstanding_reqQ[coreid].add((blkno, 'GET'))
                        else:
                            outstanding_msgQ[coreid][(blkno, rw)].append([addr, coreid])

            if Qempty :
                break

    print("\nNumber of simulated cycles for program ", filename, " =", cycle - 1)
    print("\nNumber of L1 cache hits for program ", filename, " =", L1hitcount)
    print("\nNumber of L1 cache read misses for program ", filename, " =", L1_readmisscount)
    print("\nNumber of L1 cache write misses for program ", filename, " =", L1_writemisscount)
    print("\nNumber of L1 cache upgrade misses for program ", filename, " =", L1_upgrademisscount)
    print("\nNumber of L2 cache misses for program ", filename, " =", L2misscount)

    print("\nnames and counts of all messages received by the L1 caches for program ", filename)
    dict_msgL1={}
    for i in range(8):
        for key, val in L1msgcounts[i].items():
            if key not in dict_msgL1:
                dict_msgL1[key]=[0]*8

            dict_msgL1[key][i]=val
    for key in dict_msgL1:
        print(key," = ", dict_msgL1[key])

    print("\nNames and counts of all messages received by the L2 cache banks for program ", filename)

    for key, val in L2msgcounts.items():
             print(key, '=', val)

