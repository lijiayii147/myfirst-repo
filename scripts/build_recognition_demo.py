"""Build and evaluate ONLY a synthetic shape-recognition demo; not real accuracy."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from wenmai import recognition,engine,samples


def make_examples():
    items=[]
    for label in samples.LABELS:
        for seed in range(20):
            mask,_=engine.mask_image(samples.sample(label,seed))
            items.append({'id':f'demo_{samples.LABELS.index(label)}_{seed}',
                          'asset_id':f'synthetic_{label}_{seed}','label':label,
                          'source':'Original procedural synthetic motif; not heritage imagery',
                          'feature':recognition.features(mask).tolist()})
    return items


def evaluate(items,seeds):
    rows=[]
    for label in samples.LABELS:
        for seed in seeds:
            mask,_=engine.mask_image(samples.sample(label,seed))
            prediction=recognition.rank(recognition.features(mask),items)
            rows.append({'label':label,'seed':seed,'predicted':prediction['predicted_label'],
                         'status':prediction['status'],'similarity':prediction['candidates'][0]['similarity']})
    correct=sum(r['label']==r['predicted'] for r in rows);accepted=sum(r['status']=='matched' for r in rows)
    return {'total':len(rows),'correct_including_abstentions_as_errors':correct,
            'accuracy_all_requests':correct/len(rows),'accepted':accepted,
            'coverage':accepted/len(rows),'accuracy_when_accepted':correct/accepted if accepted else None,
            'rows':rows}


def main():
    items=make_examples()
    model={'feature_version':recognition.VERSION,'data_type':'synthetic_demo_only',
           'labels':samples.LABELS,'reference_seeds':[0,19],
           'min_similarity':recognition.MIN_SIMILARITY,'min_margin':recognition.MIN_MARGIN,'examples':items}
    path=ROOT/'data'/'recognition_demo_model.json';path.write_text(json.dumps(model,ensure_ascii=False),'utf-8')
    report={'scope':'Procedural synthetic silhouettes only; cannot estimate accuracy on real heritage images',
            'reference_examples':len(items),'validation_seeds':[100,109],'test_seeds':[200,219],
            'validation':evaluate(items,range(100,110)),'test':evaluate(items,range(200,220)),
            'note':'Distinct seeds do not make these independent real artworks. Same procedural templates underlie all splits.'}
    (ROOT/'docs'/'implementation'/'recognition_evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps({k:v for k,v in report['test'].items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':main()
