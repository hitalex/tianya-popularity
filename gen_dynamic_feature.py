#coding=utf8

"""
从评论数据中构建：1）评论树，2）reply-to关系，以计算各种dynamic feature。
dynamic feature：
1. comment tree:
max depth

2. author reply-to graph:
mean degree, clustering coefficient

计算方法：
为了方便以后调用，在每个评论发布后都计算一次dynamic feature。可能会导致计算时间很长。
"""
import codecs
import os.path
from datetime import datetime

import ipdb
from igraph import *

from utils import load_id_list

# 评论数量的最大值
MAX_COMMENT = 2000

def main(section_id, base_path):
    """ 生成动态因素
    """
    post_list_path = base_path + section_id + '-post-list.txt'
    topic_list = load_id_list(post_list_path)
    topic_list = list(set(topic_list)) # 删除重复post id
    
    target_base_path = 'data-dynamic/'
    
    #topic_list = ['1377621']
    # 这里不用post_id替换topic_id的原因是：feature_dict中使用了“topic_id”作为key
    valid_topic_list = [] # 真正抽取特征的post id列表
    for topic_id in topic_list:
        path = base_path + section_id + '/' + topic_id + '-info.txt'
        if not os.path.exists(path):
            continue
        
        tpath = target_base_path + section_id + '/' + topic_id + '.txt'
        # 如果目标输出已经存在，则忽略
        if os.path.exists(tpath):
            continue
        
        f = codecs.open(path, 'r', 'utf8')
        print 'Extracting features from post file: ', path
        
        # 记录需要存储的字符串，该字符串可能较大，最大可能几M
        result_string = ""
        
        # 第一行为post本身的信息
        line = f.readline().strip()
        seg_list = line.split('[=]')
        
        if len(seg_list) != 8:
            print 'Error in the first line of topic file: ', path
            f.close()
            continue
        
        lz = seg_list[2] # LZ id for author reply to, topic_id for comment tree
        lz_user_name = seg_list[3] # 楼主的用户名
        pubdate = seg_list[5]
        num_comment = int(seg_list[6]) # NOTE：可能该文件中存储的评论数不足此数值，由于之前抓取错误导致
        
        # first line: topic info
        feature_dict = dict()
        feature_dict['topic_id'] = topic_id
        feature_dict['lz'] = lz
        feature_dict['pubdate'] = pubdate
        feature_dict['num_comment'] = num_comment
        #tf.write(str(feature_dict) + '\n')
        result_string += (str(feature_dict) + '\n')
        
        #NOTE: 因为可能在抓取时保存不完整，真正存在的评论数量可能少于第一行所表明的数字
        # 关于这一点需要检查，如果不合格，则删除
        
        # build two graphs
        comment_tree = Graph(directed=True)
        author_reply = Graph(directed=True)
        
        # 构建一个二模网络：两类节点分别是评论（包括原帖）和用户
        # 如果comment和author之间相连，则：1）author写了comment（包括原作者写了帖子），
        # 2）author评论了comment（这个comment包括原帖）
        # comment的type为False，author的type为True
        comment_author_bigraph = Graph(directed=False)
        comment_author_bigraph.add_vertex(topic_id, type=False)
        comment_author_bigraph.add_vertex(lz, type=True)
        comment_author_bigraph.add_edge(topic_id, lz)

        comment_dict = dict() # map comment id to graph index
        comment_dict[topic_id] = comment_tree.vcount()
        comment_tree.add_vertex(topic_id, date=pubdate, author=lz, depth=0)
        
        author_dict = dict() # map author_id to graph index
        author_dict[lz] = author_reply.vcount()
        author_reply.add_vertex(lz)
        
        flag = True     # 标记该文件是否合乎规范
        max_depth = 0
        # 用于描述comment tree讨论的激烈程度：根节点为0，处于depth为1的节点贡献是1，依次类推
        weighted_depth_sum = 0
        current_comment_count = 0 # 记录当前的comment数量
        for line in f:
            # 将所有的feature放入feature_dict，可以不考虑顺序
            feature_dict = dict()
            line = line.strip()
            seg_list = line.split('[=]')
            
            if len(seg_list) != 8:
                print 'Error in the comment line of topic file: ', path
                flag = False
                break
            
            cid = seg_list[0] # 评论ID
            pid = seg_list[3] # 用户的ID
            uname = seg_list[4] # 用户昵称
            pubdate = seg_list[5] # 发表时间
            replyto = seg_list[6] # 评论引用
            
            feature_dict['cid'] = cid
            feature_dict['pid'] = pid
            feature_dict['pubdate'] = pubdate
            feature_dict['replyto'] = replyto # 回复的comment的cid
            
            comment_dict[cid] = comment_tree.vcount()
            comment_tree.add_vertex(cid, date=pubdate, author=lz)
            current_comment_count += 1
            
            feature_dict['current_comment_count'] = current_comment_count
            
            comment_author_bigraph.add_vertex(cid, type=False)
            
            # if this author has once commented, it should be in author_dict
            if not pid in author_dict:
                author_dict[pid] = author_reply.vcount()
                author_reply.add_vertex(pid)
                comment_author_bigraph.add_vertex(pid, type=True)
                
            # the author-of relationship
            comment_author_bigraph.add_edge(pid, cid)
            
            replyto_pid = ''
            commenton_cid = ''
            parent_index = 0 # 在评论树上，该节点的父节点
            if replyto == '':
                commenton_cid = topic_id
                parent_index = comment_dict[commenton_cid]
                replyto_pid = lz
            else:
                commenton_cid = replyto
                parent_index = comment_dict[commenton_cid]
                replyto_pid = comment_tree.vs[parent_index]['author']
            
            comment_tree.add_edge(cid, commenton_cid)
            comment_author_bigraph.add_edge(pid, commenton_cid)
            
            # 为cid节点添加depth属性
            index = comment_dict[cid]
            if comment_tree.vs[parent_index]['depth'] == None:
                #TODO: 未知错误，举例：3211910
                flag = False
                break
            else:
                current_depth = comment_tree.vs[index]['depth'] = comment_tree.vs[parent_index]['depth'] + 1
            
            weighted_depth_sum += current_depth
            avg_weighted_depth_sum = weighted_depth_sum * 1.0 / current_comment_count
            if current_depth > max_depth:
                max_depth = current_depth
            
            # 如果是回复自己，则忽略
            if pid != replyto_pid:
                # 如果 pid指向replyto_pid已经有链接，则不考虑再次添加
                v1 = author_dict[pid]
                v2 = author_dict[replyto_pid]
                if author_reply.get_eid(v1, v2, directed=True, error=False) == -1:
                    author_reply.add_edge(v1, v2)
            
            # number of current participating commenters
            num_authors = author_reply.vcount()
            feature_dict['num_authors']             = num_authors
            
            # write statics in target file
            mean_degree             = sum(author_reply.degree()) * 1.0 / author_reply.vcount()
            avg_local_transitivity  = author_reply.transitivity_avglocal_undirected(mode='nan') # the avg of local transitivity
            clustering_coefficient  = author_reply.transitivity_undirected(mode='zero')
            assortativity           = author_reply.assortativity_degree(directed=False)
            num_componnet           = len(author_reply.components(mode=WEAK))
            reply_density           = author_reply.density(loops=True)
            # cohesion和adhesion都不合适，因为几乎每个图都有一条度为1的边
            #cohesion = author_reply.cohesion(neighbors='ignore')
            #adhesion = author_reply.adhesion()
            
            # Ref: http://igraph.sourceforge.net/doc/python/igraph.Graph-class.html#cohesive_blocks
            # cohesive_blocks only works on undirected graphs
            #author_reply_cohesive_block = author_reply.cohesive_blocks()
            #author_reply_max_cohesions = author_reply_cohesive_block.max_cohesions()

            feature_dict['mean_degree']             = mean_degree
            feature_dict['avg_local_transitivity']  = avg_local_transitivity
            feature_dict['clustering_coefficient']  = clustering_coefficient
            feature_dict['assortativity']           = assortativity
            feature_dict['num_componnet']           = num_componnet
            feature_dict['reply_density']           = reply_density
            # author-reply graph group cohesiveness
            #feature_dict['author_reply_max_cohesions'] = author_reply_max_cohesions
            
            # dynamic factor from WWW'13, Bao 
            tree_density            = comment_tree.density(loops=False)
            average_path_length     = comment_tree.average_path_length(directed=False) # do not consider directed graphs
            #diffusion_depth = comment_tree.diameter(directed=True) # diffusion depth for a tree, i.e the depth of a tree
            diffusion_depth = max_depth
            # comment tree related factors
            feature_dict['tree_density']            = tree_density
            feature_dict['diffusion_depth']         = diffusion_depth
            feature_dict['avg_weighted_depth_sum']  = avg_weighted_depth_sum
            feature_dict['avg_path_length']         = average_path_length   # Wiener index, the average distance between all paris of nodes in a cascade
            
            # the comment-author two model network properties
            ca_mean_degree              = sum(comment_author_bigraph.degree()) * 1.0 / comment_author_bigraph.vcount()
            ca_avg_local_transitivity   = comment_author_bigraph.transitivity_avglocal_undirected(mode='nan') # the avg of local transitivity
            ca_clustering_coefficient   = comment_author_bigraph.transitivity_undirected(mode='zero')
            ca_assortativity            = comment_author_bigraph.assortativity_degree(directed=False)
            ca_num_componnet            = len(comment_author_bigraph.components(mode=WEAK))
            ca_reply_density            = comment_author_bigraph.density(loops=True)
            #comment_author_cohesive_block = comment_author_bigraph.cohesive_blocks()
            #ca_max_cohesions = comment_author_cohesive_block.max_cohesions()
            
            feature_dict['ca_mean_degree']             = ca_mean_degree
            feature_dict['ca_avg_local_transitivity']  = ca_avg_local_transitivity
            feature_dict['ca_clustering_coefficient']  = ca_clustering_coefficient
            feature_dict['ca_assortativity']           = ca_assortativity
            feature_dict['ca_num_componnet']           = ca_num_componnet
            feature_dict['ca_reply_density']           = ca_reply_density
            #feature_dict['ca_max_cohesions']          = ca_max_cohesions
            
            # write feature dict to file
            #tf.write(str(feature_dict) + '\n')
            result_string += (str(feature_dict) + '\n')
            
            # do not consider threads who has more than 1000 comments
            if current_comment_count >= MAX_COMMENT:
                break

        # 如果未达到最大评论数，而且当前的评论数不足第一行所宣称的总评论数，则忽略该post
        if current_comment_count < MAX_COMMENT and num_comment != current_comment_count:
            flag = False
            
        # print dynamic feature
        #plot(comment_tree)
        #plot(author_reply)
        
        #ipdb.set_trace()
        
        #print author_reply.transitivity_undirected(mode='zero')
        #print author_reply.transitivity_avglocal_undirected(mode='zero') # the avg of local transitivity
        
        #print author_reply.assortativity_degree(False)
        f.close()
        
        if flag:
            valid_topic_list.append(topic_id)
            # 输出到文件
            print 'Saving: ', tpath
            tf = codecs.open(tpath, 'w', 'utf8')
            tf.write(result_string)
            tf.close()
            
    # 保存所有有效的讨论帖id
    path = target_base_path + section_id + '-post-list-feature.txt'
    f = codecs.open(path, 'w', 'utf8')
    for topic_id in valid_topic_list:
        f.write(topic_id + '\n')
    f.close()
        
if __name__ == '__main__':
    import sys
    section_id = sys.argv[1]
    #section_id = 'free'
    base_path = '/home/kongqingchao/dataset/tianya-forum/'
    
    main(section_id, base_path)
