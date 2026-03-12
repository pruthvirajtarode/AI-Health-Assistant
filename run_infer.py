from src import pipeline
import json, sys
print('CALLING INFER...')
try:
	res = pipeline.infer('fever and headache', debug=True)
	print('INFER DONE, result:')
	print(json.dumps(res, ensure_ascii=False, indent=2))
except Exception as e:
	import traceback
	print('INFER ERROR:', e)
	traceback.print_exc()
sys.stdout.flush()
