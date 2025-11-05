ps -ef|grep app.py | awk '{print $2}' |xargs kill 
nohup streamlit run app.py --server.headless true > logs/parse_data_serve_1105.log 2>&1 &