#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import string
import re 
import itertools
import csv

#from nltk.corpus import stopwords
from stop_words import get_stop_words
from textblob import TextBlob
from textblob_fr import PatternTagger, PatternAnalyzer
# requires nltk 3.2.1

#import networkx as nx
from itertools import groupby
import igraph
from nltk.stem.snowball import FrenchStemmer
 
def hasNumbers(inputString):
     return bool(re.search(r'\d', inputString))
               
def csv_writer(data, path):
    """
    Write data to a CSV file path
    """
    with open(path, "wb") as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(("Word","Specificity Score"))
        for line in data:
            writer.writerow(line)
             
def clean_text_simple(text, remove_stopwords=True, pos_filtering=True, stemming=True, lang="fr"):
    
    """Returns a list of tokens 

    Parameters
    ----------
    text : string 
    remove_stopwords : boolean
    pos_filtering : boolean    
    lang : string
        default : "fr"
        
    Returns
    -------
    tokens : list of strings (tokens)

    Examples
    --------
    >>> from library_graph import clean_text_simple
    >>> text = "Je n'aime pas du tout aller à la plage"
    >>> tokens = clean_text_simple(text) => [u'aime', u'aller', u'plage']
    
    Warning !! L'encoding doit-être en utf-8
    
    """
    
    if text :
        stpwds = get_stop_words(lang) #stopwords
        punct = string.punctuation.replace('-', '')
        punct = punct.replace('_', '')
        punct = punct.replace('\'', '')         
        # convert to lower case
        text = text.lower()
               
        # remove punctuation (preserving intra-word dashes)
        text = ''.join(l for l in text if l not in punct)
        
        # strip extra white space
        text = re.sub(u'’',u' ',text)
        text = re.sub('\'',' ',text)
        text = re.sub('\n',' ',text)
        text = re.sub(' +',' ',text) 
        text = re.sub('\d+,\d+',' ',text)
        # strip all non-alphanumeric characters at the end or beginning of the sentence
        pattern = re.compile('[\W_]+')
        text = pattern.sub('', text)
        pattern = re.compile('[{\(\[].*}+')
        text = pattern.sub('', text)
        pattern = re.compile('[.*}]+')
        text = pattern.sub('', text)
        
        if not text :
            return []
        # tokenize (split based on whitespace)
        tokens = text.split(' ')
        
        if pos_filtering == True:
            # apply POS-tagging
            blob = TextBlob(text, pos_tagger=PatternTagger(), analyzer=PatternAnalyzer())
            tagged_tokens = blob.tags
            # retain only nouns and adjectives
            tokens_keep = []
            for i in range(len(tagged_tokens)):
                item = tagged_tokens[i]
                if (
                item[1] == 'NN' or
                item[1] == 'NNS' or
                item[1] == 'VB' or
                item[1] == 'VBN' or  
                item[1] == 'VBG' or    
                item[1] == 'JJ' or
                item[1] == 'JJS' or
                item[1] == 'JJR' 
                ):  
                    #tokens_keep.append(item[0])
                    if "_" in item[0] :
                        grams = item[0].split("_") 
                        if len(grams) > 1 :
                                if len(grams[0])>0 and grams[0] not in stpwds : #we want to get rid of grams that are just here because of articles
                                      tokens_keep.append(item[0])
                                else : 
                                    tok = "_".join(grams[1:])
                                    tokens_keep.append(tok)  
                    else :
                        tokens_keep.append(item[0])    
            
            tokens = tokens_keep
            
        if remove_stopwords:
            # remove stopwords
            tokens = [token.lower() for token in tokens if token not in stpwds and len(token) > 2]
            
        if stemming :  
             stemmer = FrenchStemmer()
             tokens_stemmed = list()
             for token in tokens:
                 tokens_stemmed.append(stemmer.stem(token))
             tokens = tokens_stemmed
            
        tokens = [x[0].lower() for x in groupby(tokens) if x[0] not in punct and not hasNumbers(x[0]) and x[0] not in stpwds and len(token)>2] 
        n = len(tokens)   
        for i in range(n):
            while tokens[i].endswith('_'):
                tokens[i] = tokens[i][:-1] 
            while tokens[i].startswith('_'):
                tokens[i] = tokens[i][1:]    
        return(tokens)

def terms_to_graph(terms, w):
    
    """Returns a weighted graph from a list of terms (the tokens from the pre-processed text) e.g., ['quick','brown','fox'] 
    Edges are weighted based on term co-occurence within a sliding window of fixed size 'w'
    
    Parameters
    ----------
    terms : list of strings
    w : sliding_window size    
    
    Returns
    -------
    g : directed weigthed graph
    
    """
  
    from_to = {}
    
    # create initial complete graph (first w terms)
    terms_temp = terms[0:w]
    indexes = list(itertools.combinations(range(w), r=2))
    
    new_edges = []
    
    for my_tuple in indexes:
        new_edges.append(tuple([terms_temp[i] for i in my_tuple]))
    
    for new_edge in new_edges:
        if new_edge in from_to:
            from_to[new_edge] += 1
        else:
            from_to[new_edge] = 1
    
    # then iterate over the remaining terms
    for i in xrange(w, len(terms)):
        # term to consider
        considered_term = terms[i]
        # all terms within sliding window
        terms_temp = terms[(i-w+1):(i+1)]
        
        # edges to try
        candidate_edges = []
        for p in xrange(w-1):
            candidate_edges.append((terms_temp[p],considered_term))
            
        for try_edge in candidate_edges:
        
            # if not self-edge
            if try_edge[1] != try_edge[0]:
                
                # if edge has already been seen, update its weight
                if try_edge in from_to:
                    from_to[try_edge] += 1
                
                # if edge has never been seen, create it and assign it a unit weight     
                else:
                    from_to[try_edge] = 1
    
    # create empty graph
#    g = nx.Graph()
#    
#    # add vertices
#    g.add_nodes_from(sorted(set(terms)))   
#    
#    # add edges, direction is preserved since the graph is directed
#    weighted_edges = [(key[0], key[1], val) for key, val in from_to.iteritems()]
#    
#    # set edge and vertice weights
#    g.add_weighted_edges_from(weighted_edges)
    
    # create empty graph
    g = igraph.Graph(directed=True)
    
    # add vertices
    g.add_vertices(sorted(set(terms)))
    
    # add edges, direction is preserved since the graph is directed
    g.add_edges(from_to.keys())
    
    # set edge and vertice weights
    g.es['weight'] = from_to.values() # based on co-occurence within sliding window
    g.vs['weight'] = g.strength(weights=from_to.values()) # weighted degree
    
    return(g)



        
