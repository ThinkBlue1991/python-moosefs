#!/usr/bin/env python2
'''
A Python library for gathering information from MooseFS
'''
import socket
import struct
import time
import traceback
import sys

masterhost = 'mfsmaster'
masterport = 9421
mastername = 'MooseFS'

def mysend(socket,msg):
    totalsent = 0
    while totalsent < len(msg):
        sent = socket.send(msg[totalsent:])
        if sent == 0:
            raise RuntimeError("socket connection broken")
        totalsent = totalsent + sent 

def myrecv(socket,leng):
    msg = '' 
    while len(msg) < leng:
        chunk = socket.recv(leng-len(msg))
        if chunk == '':
            raise RuntimeError("socket connection broken")
        msg = msg + chunk
    return msg

# check version
masterversion = (0,0,0)
try:
    s = socket.socket()
    s.connect((masterhost,masterport))
    mysend(s,struct.pack(">LL",510,0))
    header = myrecv(s,8)
    cmd,length = struct.unpack(">LL",header)
    data = myrecv(s,length)
    if cmd==511:
        if length==52:
            masterversion = (1,4,0)
        elif length==60:
            masterversion = (1,5,0)
        elif length==68:
            masterversion = struct.unpack(">HBB",data[:4])
except:
    pass

def mfs_info(INmatrix=0):
    # For INmatrix, 0 means all, 1 means regular
    info = {}
    try:
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",510,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==511 and length==52:
            data = myrecv(s,length)
            total,avail,trspace,trfiles,respace,refiles,nodes,chunks,tdcopies = struct.unpack(">QQQLQLLLL",data)
            info = {
                'total_space':          total,
                'avail_space':          avail,
                'trash_space':          trspace,
                'trash_files':          trfiles,
                'reserved_space':       respace,
                'reserved_files':       refiles,
                'all_fs_objects':       nodes,
                'chunks':               chunks,
                'regular_chunk_copies': tdcopies,
            }
        elif cmd==511 and length==60:
            data = myrecv(s,length)
            total,avail,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,tdcopies = struct.unpack(">QQQLQLLLLLL",data)
            info = {
                'total_space':          total,
                'avail_space':          avail,
                'trash_space':          trspace,
                'trash_files':          trfiles,
                'reserved_space':       respace,
                'reserved_files':       refiles,
                'all_fs_objects':       nodes,
                'directories':          dirs,
                'files':                files,
                'chunks':               chunks,
                'regular_chunk_copies': tdcopies,
            }
        elif cmd==511 and length==68:
            data = myrecv(s,length)
            v1,v2,v3,total,avail,trspace,trfiles,respace,refiles,nodes,dirs,files,chunks,allcopies,tdcopies = struct.unpack(">HBBQQQLQLLLLLLL",data)
            ver = '.'.join([str(v1), str(v2), str(v3)])
            info = {
                'version':              ver,
                'total_space':          total,
                'avail_space':          avail,
                'trash_space':          trspace,
                'trash_files':          trfiles,
                'reserved_space':       respace,
                'reserved_files':       refiles,
                'all_fs_objects':       nodes,
                'directories':          dirs,
                'files':                files,
                'chunks':               chunks,
                'all_chunk_copies':     allcopies,
                'regular_chunk_copies': tdcopies,
            }
        else:
            info = {
                'error': 'unrecognized answer from MFSmaster',
            }
        s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    # All chunks state matrix
    matrix = []
    if masterversion>=(1,5,13):
        try:
            s = socket.socket()
            s.connect((masterhost,masterport))
            if masterversion>=(1,6,10):
                mysend(s,struct.pack(">LLB",516,1,INmatrix))
            else:
                mysend(s,struct.pack(">LL",516,0))
            header = myrecv(s,8)
            cmd,length = struct.unpack(">LL",header)
            if cmd==517 and length==484:
                # This will generate a matrix of goals, from 0 to 10+
                # for both rows and columns. It does not include totals.
                for i in xrange(11):
                    data = myrecv(s,44)
                    matrix.append(list(struct.unpack(">LLLLLLLLLLL",data)))
            s.close()
        except Exception:
            traceback.print_exc(file=sys.stdout)

    # Chunk operations info
    chunk_info = {}
    try:
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",514,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==515 and length==52:
            data = myrecv(s,length)
            loopstart,loopend,del_invalid,ndel_invalid,del_unused,ndel_unused,del_dclean,ndel_dclean,del_ogoal,ndel_ogoal,rep_ugoal,nrep_ugoal,rebalnce = struct.unpack(">LLLLLLLLLLLLL",data[:52])
        chunk_info = {
            'loop_start':                     loopstart,
            'loop_end':                       loopend,
            'invalid_deletions':              del_invalid,
            'invalid_deletions_out_of':       del_invalid+ndel_invalid,
            'unused_deletions':               del_unused,
            'unused_deletions_out_of':        del_unused+ndel_unused,
            'disk_clean_deletions':           del_dclean,
            'disk_clean_deletions_out_of':    del_dclean+ndel_dclean,
            'over_goal_deletions':            del_ogoal,
            'over_goal_deletions_out_of':     del_ogoal+ndel_ogoal,
            'replications_under_goal':        rep_ugoal,
            'replications_under_goal_out_of': rep_ugoal+nrep_ugoal,
            'replocations_rebalance':         rebalnce,
        }
        s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    # Filesystem check info
    check_info = {}
    try:
        out = []
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",512,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==513 and length>=36:
            data = myrecv(s,length)
            loopstart,loopend,files,ugfiles,mfiles,chunks,ugchunks,mchunks,msgbuffleng = struct.unpack(">LLLLLLLLL",data[:36])
            messages = ''
            truncated = ''
            if loopstart>0:
                if msgbuffleng>0:
                    if msgbuffleng==100000:
                        truncated = 'first 100k'
                    else:
                        truncated = 'no'
                    messages = data[36:]
            else:
                messages = 'no data'
            check_info = {
                'check_loop_start_time': loopstart,
                'check_loop_end_time':   loopend,
                'files':                 files,
                'under_goal_files':      ugfiles,
                'missing_files':         mfiles,
                'chunks':                chunks,
                'under_goal_chunks':     ugchunks,
                'missing_chunks':        mchunks,
                'msgbuffleng':           msgbuffleng,
                'important_messages':    messages,
                'truncated':             truncated,
            }
        s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    ret = {
        'info': info,
        'matrix': matrix,
        'chunk_info': chunk_info,
        'check_info': check_info,
    }
    return ret

def mfs_servers():
    servers = []
    try:
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",500,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==501 and masterversion>=(1,5,13) and (length%54)==0:
            data = myrecv(s,length)
            n = length/54
            for i in xrange(n):
                d = data[i*54:(i+1)*54]
                v1,v2,v3,ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt = struct.unpack(">HBBBBBBHQQLQQLL",d)
                host = ''
                try:
                    host = (socket.gethostbyaddr("%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)))[0]
                except Exception:
                    host = "(unresolved)"
                ip = '.'.join([str(ip1), str(ip2), str(ip3), str(ip4)])
                ver = '.'.join([str(v1), str(v2), str(v3)])
                percent_used = ''
                if (total>0):
                    percent_used = (used*100.0)/total
                else:
                    percent_used = '-'
                tdpercent_used = ''
                if (tdtotal>0):
                    tdpercent_used = (tdused*100.0)/tdtotal
                else:
                    tdpercent_used = ''
                servers.append({
                    'host':           host,
                    'ip':             ip,
                    'version':        ver,
                    'port':           port,
                    'used':           used,
                    'total':          total,
                    'chunks':         chunks,
                    'percent_used':   percent_used,
                    'tdused':         tdused,
                    'tdtotal':        tdtotal,
                    'tdchucnks':      tdchunks,
                    'tdpercent_used': tdpercent_used,
                    'errcount':       errcnt,
                })
        elif cmd==501 and masterversion<(1,5,13) and (length%50)==0:
            data = myrecv(s,length)
            n = length/50
            for i in xrange(n):
                d = data[i*50:(i+1)*50]
                ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt = struct.unpack(">BBBBHQQLQQLL",d)
                try:
                    host = (socket.gethostbyaddr("%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)))[0]
                except Exception:
                    host = "(unresolved)"
                ip = '.'.join([str(ip1), str(ip2), str(ip3), str(ip4)])
                percent_used = ''
                if (total>0):
                    percent_used = (used*100.0)/total
                else:
                    percent_used = '-'
                tdpercent_used = ''
                if (tdtotal>0):
                    tdpercent_used = (tdused*100.0)/tdtotal
                else:
                    tdpercent_used = ''
                servers.append({
                    'host':           host,
                    'ip':             ip,
                    'port':           port,
                    'used':           used,
                    'total':          total,
                    'chunks':         chunks,
                    'percent_used':   percent_used,
                    'tdused':         tdused,
                    'tdtotal':        tdtotal,
                    'tdchucnks':      tdchunks,
                    'tdpercent_used': tdpercent_used,
                    'errcount':       errcnt,
                })
        s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    # Metadata backup loggers
    mbloggers = []
    if masterversion>=(1,6,5):
        try:
            s = socket.socket()
            s.connect((masterhost,masterport))
            mysend(s,struct.pack(">LL",522,0))
            header = myrecv(s,8)
            cmd,length = struct.unpack(">LL",header)
            if cmd==523 and (length%8)==0:
                data = myrecv(s,length)
                n = length/8
                for i in xrange(n):
                    d = data[i*8:(i+1)*8]
                    v1,v2,v3,ip1,ip2,ip3,ip4 = struct.unpack(">HBBBBBB",d)
                    ip = '.'.join([str(ip1), str(ip2), str(ip3), str(ip4)])
                    ver = '.'.join([str(v1), str(v2), str(v3)])
                    try:
                        host = (socket.gethostbyaddr("%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)))[0]
                    except Exception:
                        host = "(unresolved)"
                    mbloggers.append((host,ip,ver))
            s.close()
        except Exception:
            traceback.print_exc(file=sys.stdout)
    ret = {
        'servers':                 servers,
        'metadata_backup_loggers': mbloggers,
    }
    return ret

def mfs_disks(HDtime=max, HDperiod=min):
    # HDtime can be avg or max
    # HDperiod can be min, hour or day
    try:
        # get cs list
        hostlist = []
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",500,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==501 and masterversion>=(1,5,13) and (length%54)==0:
            data = myrecv(s,length)
            n = length/54
            servers = []
            for i in xrange(n):
                d = data[i*54:(i+1)*54]
                v1,v2,v3,ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt = struct.unpack(">HBBBBBBHQQLQQLL",d)
                hostlist.append((v1,v2,v3,ip1,ip2,ip3,ip4,port))
        elif cmd==501 and masterversion<(1,5,13) and (length%50)==0:
            data = myrecv(s,length)
            n = length/50
            servers = []
            for i in xrange(n):
                d = data[i*50:(i+1)*50]
                ip1,ip2,ip3,ip4,port,used,total,chunks,tdused,tdtotal,tdchunks,errcnt = struct.unpack(">BBBBHQQLQQLL",d)
                hostlist.append((1,5,0,ip1,ip2,ip3,ip4,port))
        s.close()

        # get hdd lists one by one
        hdd = []
        for v1,v2,v3,ip1,ip2,ip3,ip4,port in hostlist:
            hostip = "%u.%u.%u.%u" % (ip1,ip2,ip3,ip4)
            try:
                hoststr = (socket.gethostbyaddr(hostip))[0]
            except Exception:
                hoststr = "(unresolved)"
            if port>0:
                if (v1,v2,v3)<=(1,6,8):
                    s = socket.socket()
                    s.connect((hostip,port))
                    mysend(s,struct.pack(">LL",502,0))
                    header = myrecv(s,8)
                    cmd,length = struct.unpack(">LL",header)
                    if cmd==503:
                        data = myrecv(s,length)
                        while length>0:
                            plen = ord(data[0])
                            host_path = "%s:%u:%s" % (hoststr,port,data[1:plen+1])
                            ip_path = "%s:%u:%s" % (hostip,port,data[1:plen+1])
                            flags,errchunkid,errtime,used,total,chunkscnt = struct.unpack(">BQLQQL",data[plen+1:plen+34])
                            length -= plen+34
                            data = data[plen+34:]
                            hdd.append((ip_path,host_path,flags,errchunkid,errtime,used,total,chunkscnt,0,0,0,0,0,0,0,0,0,0,0,0))
                    s.close()
                else:
                    s = socket.socket()
                    s.connect((hostip,port))
                    mysend(s,struct.pack(">LL",600,0))
                    header = myrecv(s,8)
                    cmd,length = struct.unpack(">LL",header)
                    if cmd==601:
                        data = myrecv(s,length)
                        while length>0:
                            entrysize = struct.unpack(">H",data[:2])[0]
                            entry = data[2:2+entrysize]
                            data = data[2+entrysize:]
                            length -= 2+entrysize;

                            plen = ord(entry[0])
                            host_path = "%s:%u:%s" % (hoststr,port,entry[1:plen+1])
                            ip_path = "%s:%u:%s" % (hostip,port,entry[1:plen+1])
                            flags,errchunkid,errtime,used,total,chunkscnt = struct.unpack(">BQLQQL",entry[plen+1:plen+34])
                            rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = (0,0,0,0,0,0,0,0,0,0,0)
                            if entrysize==plen+34+144:
                                if HDperiod == 'min':
                                    rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34:plen+34+48])
                                elif HDperiod == 'hour':
                                    rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34+48:plen+34+96])
                                elif HDperiod == 'day':
                                    rbytes,wbytes,usecreadsum,usecwritesum,rops,wops,usecreadmax,usecwritemax = struct.unpack(">QQQQLLLL",entry[plen+34+96:plen+34+144])
                            elif entrysize==plen+34+192:
                                if HDperiod == 'min':
                                    rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34:plen+34+64])
                                elif HDperiod == 'hour':
                                    rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34+64:plen+34+128])
                                elif HDperiod == 'day':
                                    rbytes,wbytes,usecreadsum,usecwritesum,usecfsyncsum,rops,wops,fsyncops,usecreadmax,usecwritemax,usecfsyncmax = struct.unpack(">QQQQQLLLLLL",entry[plen+34+128:plen+34+192])
                            if usecreadsum>0:
                                rbw = rbytes*1000000/usecreadsum
                            else:
                                rbw = 0
                            if usecwritesum+usecfsyncsum>0:
                                wbw = wbytes*1000000/(usecwritesum+usecfsyncsum)
                            else:
                                wbw = 0
                            if HDtime == 'avg':
                                if rops>0:
                                    rtime = usecreadsum/rops
                                else:
                                    rtime = 0
                                if wops>0:
                                    wtime = usecwritesum/wops
                                else:
                                    wtime = 0
                                if fsyncops>0:
                                    fsynctime = usecfsyncsum/fsyncops
                                else:
                                    fsynctime = 0
                            else:
                                rtime = usecreadmax
                                wtime = usecwritemax
                                fsynctime = usecfsyncmax
                            if flags == 1:
                                if masterversion>=(1,6,10):
                                    status = 'marked for removal'
                                else:
                                    status = 'to be empty'
                            elif flags == 2:
                                status = 'damaged'
                            elif flags == 3:
                                if masterversion>=(1,6,10):
                                    status = 'damaged, marked for removal'
                                else:
                                    status = 'damaged, to be empty'
                            else:
                                status = 'ok'
                            if errtime==0 and errchunkid==0:
                                lerror = 'no errors'
                            else:
                                lerror = time.localtime(errtime)
                            if rops>0:
                                rbsize = rbytes/rops
                            else:
                                rbsize = 0
                            if wops>0:
                                wbsize = wbytes/wops
                            else:
                                wbsize = 0
                            if (total>0):
                                percent_used = (used*100.0)/total
                            else:
                                percent_used = '-'
                            hdd.append({
                                'ip_path': ip_path,
                                'host_path': host_path,
                                'flags': flags,
                                'errchunkid': errchunkid,
                                'errtime': errtime,
                                'used': used,
                                'total': total,
                                'chunkscnt': chunkscnt,
                                'rbw': rbw,
                                'wbw': wbw,
                                'rtime': rtime,
                                'wtime': wtime,
                                'fsynctime': fsynctime,
                                'read_ops': rops,
                                'write_ops': wops,
                                'fsyncops': fsyncops,
                                'read_bytes': rbytes,
                                'write_bytes': wbytes,
                                'usecreadsum': usecreadsum,
                                'usecwritesum': usecwritesum,
                                'status': status,
                                'lerror': lerror,
                                'rbsize': rbsize,
                                'wbsize': wbsize,
                                'percent_used': percent_used,
                            })
                    s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    return hdd

def mfs_exports():
    servers = []
    try:
        s = socket.socket()
        s.connect((masterhost,masterport))
        mysend(s,struct.pack(">LL",520,0))
        header = myrecv(s,8)
        cmd,length = struct.unpack(">LL",header)
        if cmd==521 and masterversion>=(1,5,14):
            data = myrecv(s,length)
            pos = 0
            while pos<length:
                fip1,fip2,fip3,fip4,tip1,tip2,tip3,tip4,pleng = struct.unpack(">BBBBBBBBL",data[pos:pos+12])
                ipfrom = "%d.%d.%d.%d" % (fip1,fip2,fip3,fip4)
                ipto = "%d.%d.%d.%d" % (tip1,tip2,tip3,tip4)
                pos+=12
                path = data[pos:pos+pleng]
                pos+=pleng
                if masterversion>=(1,6,1):
                    v1,v2,v3,exportflags,sesflags,rootuid,rootgid,mapalluid,mapallgid = struct.unpack(">HBBBBLLLL",data[pos:pos+22])
                    pos+=22
                else:
                    v1,v2,v3,exportflags,sesflags,rootuid,rootgid = struct.unpack(">HBBBBLL",data[pos:pos+14])
                    mapalluid = 0
                    mapallgid = 0
                    pos+=14
                ver = "%d.%d.%d" % (v1,v2,v3)
                if path=='.':
                    meta=1
                else:
                    meta=0
                servers.append((ipfrom,ipto,path,meta,ver,exportflags,sesflags,rootuid,rootgid,mapalluid,mapallgid))
        s.close()
    except Exception:
        traceback.print_exc(file=sys.stdout)

    return servers

status = mfs_exports()
print status
sys.exit(0)
