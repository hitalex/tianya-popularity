#coding=utf8

"""
功能：从已经抓取的讨论帖数据中查找引用。
原因：在进行抓取时，发现有些引用找不到，而引用信息又非常重要，所以这里重新扫描已经抓取的文件，
并找到真正的引用信息
"""
import re
import os
import codecs

from utils import load_id_list

# 评论数量的最大值
MAX_COMMENT = 5000

# 引用评论的格式
# NOTE: 用户名中不能包含@，以及其他空白字符
regex_quote = re.compile(ur'@(?P<uname>[^@\s]+?)\s+(?P<lou_index>\d+)楼\s+(?P<date>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', re.UNICODE)

def fix_quote_info(source_path, target_path, post_list):
    """ 检验评论的引用信息
    """
    for post_id in post_list:
        spath = source_path + post_id + '-info.txt'
        if not os.path.exists(spath):
            continue
        
        sf = codecs.open(spath, 'r', 'utf8')
        tpath = target_path + post_id + '-info.txt'
        tf = codecs.open(tpath, 'w', 'utf8')
        
        # 跳过第一行，因为此行是对该讨论帖的信息
        sf.readline()
        
        # uname+strdate ==> cid
        comment_info_dict = dict() # 可以加快判断速度
        flag = False
        for sline in sf:
            seg_list = sline.strip().split('[=]')
            # 分别抽取 cid，user name，日期，quote cid
            cid = seg_list[0]
            uname = seg_list[4]
            strdate = seg_list[5]
            reply_to = seg_list[6]
            content = seg_list[7]
            
            if cid == '189' or cid == '221':
                import ipdb; ipdb.set_trace()
            
            comment_info_dict[uname+strdate] = cid
            # 如果超过最大评论数，则忽略剩下的评论
            if len(comment_info_dict) > MAX_COMMENT:
                flag = True
                break
                
            mlist = list(regex_quote.finditer(content))
            if reply_to == '' and len(mlist) > 0:
                m = mlist[-1]
                quote_uname = m.group('uname') 
                quote_strdate = m.group('date')
                key = quote_uname + quote_strdate
                print '\nCurrent lou: ', cid
                if key in comment_info_dict:
                    quote_cid = comment_info_dict[key]
                    seg_list[6] = quote_cid
                    tf.write('[=]'.join(seg_list) + '\n')
                    print 'Find missing quote in post: ', post_id
                    print 'Comment content: ', content
                else:
                    tf.write(sline + '\n')
                    print 'Error in finding quote in post: ', post_id
                    print 'Matched quote: ', m.group()
                    print 'Comment content: ', content
            else:
                tf.write(sline + '\n')
        
        sf.close()
        tf.close()
        
if __name__ == '__main__':
    import codecs
    import sys
    writer = codecs.getwriter('utf8')
    sys.stdout = writer(sys.stdout) # for writing to pipes
    
    section_id = 'free'
    base_path = '/home/kqc/dataset/tianya-forum/'
    
    source_path = base_path + 'test/'
    target_path = '/home/kqc/dataset/tianya-forum-fixquote/' + section_id + '/'
    
    post_list_path = base_path + section_id + '-post-list.txt'
    post_list = load_id_list(post_list_path)
    
    post_list = ['3164851']
    fix_quote_info(source_path, target_path, post_list)
