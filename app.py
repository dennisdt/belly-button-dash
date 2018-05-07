import pandas as pd
import numpy as np

import sqlalchemy
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

import plotly.plotly as py
import plotly.graph_objs as go

import dash
from dash import Dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html

# Initialize Dash app (similar to Flask)
app = Dash(__name__)
server = app.server

###################################
#                                 #
# Connect to DB using SQL Alchemy #
#                                 #
###################################
engine = create_engine("sqlite:///belly_button_biodiversity.sqlite")

# reflect an existing database into a new model
Base = automap_base()
# reflect the tables
Base.prepare(engine, reflect=True)

# Save references to each table
Samples_Metadata = Base.classes.samples_metadata
OTU = Base.classes.otu
Samples = Base.classes.samples

# Create our session (link) from Python to the DB
session = Session(engine)

def names():

    # Use Pandas to perform the sql query
    stmt = session.query(Samples).statement
    df = pd.read_sql_query(stmt, session.bind)
    df.set_index('otu_id', inplace=True)

    # Return a list of the column names (sample names)
    return list(df.columns)

def otu():
    
    results = session.query(OTU.lowest_taxonomic_unit_found).all()

    # Use numpy ravel to extract list of tuples into a list of OTU descriptions
    otu_list = list(np.ravel(results))
    return otu_list

def sample_metadata(sample):
   
    sel = [Samples_Metadata.SAMPLEID, Samples_Metadata.ETHNICITY,
           Samples_Metadata.GENDER, Samples_Metadata.AGE,
           Samples_Metadata.LOCATION, Samples_Metadata.BBTYPE]

    
    # matches the numeric value of `SAMPLEID` from the database
    results = session.query(*sel).\
        filter(Samples_Metadata.SAMPLEID == sample[3:]).all()

    # Create a dictionary entry for each row of metadata information
    sample_metadata = {}
    for result in results:
        sample_metadata['SAMPLEID'] = result[0]
        sample_metadata['ETHNICITY'] = result[1]
        sample_metadata['GENDER'] = result[2]
        sample_metadata['AGE'] = result[3]
        sample_metadata['LOCATION'] = result[4]
        sample_metadata['BBTYPE'] = result[5]

    return sample_metadata

def sample_wfreq(sample):
    """Return the Weekly Washing Frequency as a number."""

    # `sample[3:]` strips the `BB_` prefix
    results = session.query(Samples_Metadata.WFREQ).\
        filter(Samples_Metadata.SAMPLEID == sample[3:]).all()
    wfreq = np.ravel(results)

    # Return only the first integer value for washing frequency
    return int(wfreq[0])


def samples(sample):
    
    stmt = session.query(Samples).statement
    df = pd.read_sql_query(stmt, session.bind)

    # Make sure that the sample was found in the columns, else throw an error
    if sample not in df.columns:
        return f"Error! Sample: {sample} Not Found!"

    # Return any sample values greater than 1
    df = df[df[sample] > 1]

    # Sort the results by sample in descending order
    df = df.sort_values(by=sample, ascending=0)

    # Format the data to send as json
    data = [{
        "otu_ids": df[sample].index.values.tolist(),
        "sample_values": df[sample].values.tolist()
    }]
    return data

#################################
#                               #
#      Build Dash dashboard     #
#                               #
#################################

# initialize list of names
names = names()

app.layout = html.Div(className="container", children=[
    html.Div(className="col-md-12 jumbotron text-center", children=[
        html.H1(
            children='Belly Button Biodiversity',
            style={
                'textAlign': 'center'
            }
        ),

        html.P(children='Use the interactive charts below to explore the dataset', style={
            'textAlign': 'center'
        })
    ]),
    # new row
    html.Div(className="row", children=[
        # size 2
        html.Div(className="col-md-2", children=[
            html.Div(className="well", style={
            	'min-height': 20, 
            	'padding': "19px", 
            	'margin-bottom': 20, 
            	'background-color': '#f5f5f5', 
            	'border-style': 'solid', 
            	'border-width': 1, 
            	'border-color': '#e3e3e3', 
            	'border-radius': 4
            	}, 
            	children=[
	                html.H5(children='Select Sample:', 
	                        style={
	                        	'font-size': 14,
	                            'textAlign': 'center'
	                    }
	                ),

	                dcc.Dropdown(
	                    id='name_dropdown',
	                    options=[
	                        {'label': name, 'value': name} for name in names],
	                    value=names[0]
	                )
            	]
            ),

            html.Div(className="panel panel-primary", style={
            	'border-color': '#337ab7',
            	'border-style': 'solid', 
            	'border-width': 1, 
            	'border-radius': 4,
            	'background-color': '#fff',
            	'margin-bottom': 20
            	}, 
            	children=[
                html.Div(className="panel-heading", 
                	style={
                		'padding': '10px 15px',
                		'border-bottom': 'solid',
                		'border-top-left-radius': 3,
                		'border-top-right-radius': 3,                		
                		'color': '#fff',
                		'background-color': '#337ab7'
                	},
                	children=[
	                    html.H3(className="panel-title", children='Sample MetaData', 
	                    	style={
		                		"font-size": 16,
		                		"color": 'inherit',
		                		"margin-top": 0,
		                		"margin-bottom": 0,
								"textAlign": 'center'
	                		}
	                	)
                	]
            	),
                html.Div(className="panel-body", id="sample-metadata", 
                	style={
                		'padding': "15px"                	}
                )
            ])
        ]),

        # size 5 for piechart same row
        html.Div(className="col-md-5", children=[
            dcc.Graph(id='donut-chart')
        ]),

        # size 5 for gauge same row
        html.Div(className="col-md-5", children=[
            dcc.Graph(id='gauge')
        ])
    ]),

	html.Div(className="row", children=[
		html.Div(className="col-md-12", children=[
			dcc.Graph(id='bubble-plot')
		])
	])
])

###############################################
#                                             #
#  Import your CSS and JS dependent libaries  #
#                                             #
###############################################

external_css = ["https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css",
                "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css"]

for css in external_css:
    app.css.append_css({"external_url": css})

external_js = ["http://code.jquery.com/jquery-3.3.1.min.js",
               "https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0/js/bootstrap.min.js"]

for js in external_js:
    app.scripts.append_script({"external_url": js})

##################################################
#                                                #
#       Callback Functions to update plots       #
#                                                #
##################################################

# metadata
@app.callback(Output('sample-metadata', 'children'), [Input('name_dropdown', 'value')])
def update_metadata(name_dropdown):
	meta = sample_metadata(name_dropdown)

	return [
		html.H6(style={'font-size': 12}, children="AGE" + ": " + str(meta["AGE"])),
		html.H6(style={'font-size': 12}, children="BBTYPE" + ": " + str(meta["BBTYPE"])),
		html.H6(style={'font-size': 12}, children="ETHNICITY" + ": " + str(meta["ETHNICITY"])),
		html.H6(style={'font-size': 12}, children="GENDER" + ": " + str(meta["GENDER"])),
		html.H6(style={'font-size': 12}, children="LOCATION" + ": " + str(meta["LOCATION"])),
		html.H6(style={'font-size': 12}, children="SAMPLEID" + ": " + str(meta["SAMPLEID"]))
		]

# pie chart
@app.callback(Output('donut-chart', 'figure'), [Input('name_dropdown', 'value')])
def update_pie(name_dropdown):
    data_sample = samples(name_dropdown)
    labels = data_sample[0]['otu_ids']

    return {
            "data": [
                {
                  "values": data_sample[0]["sample_values"][0:10],
                  "labels": data_sample[0]["otu_ids"][0:10],
                  "hovertext": labels[0:10],
                  "hoverinfo":"hovertext",
                  "hole": .4,
                  "type": "pie",
                  "marker": {
                      "colors": ['#add8e6','#b7dde5','#c0e1e5','#cae5e4','#d3e9e4','#dceee3','#e4f2e2','#eef7e1','#f6fae1','#ffffe0']
                  }
                }],
            "layout": {
                    "title":"OTU Percent",
                    "annotations": [
                        {
                            "font": {
                                "size": 20
                            },
                            "showarrow": False,
                            "text": " ",
                            "x": 0.20,
                            "y": 0.5
                        }
                    ]
                }
            }


# gauge
@app.callback(Output('gauge', 'figure'), [Input('name_dropdown', 'value')])
def update_gauge(name_dropdown):
    # query the sample
    wfreq = sample_wfreq(name_dropdown)
    level = wfreq*20
    degrees = 180 - level
    radius = .5
    radians = degrees * np.pi / 180
    x = radius * np.cos(radians)
    y = radius * np.sin(radians)
    main_path = 'M -.0 -0.05 L .0 0.05 L '
    path_x = str(x)
    path_y = str(y)

    path = main_path + path_x + " " + path_y + " " + "Z"

    return {
            "data": [
                {
                    "type": 'scatter',
                    "x": [0], 
                    "y":[0],
                    "marker": {"size": 12, "color":'850000'},
                    "showlegend": False,
                    "name": 'Freq',
                    "text": level,
                    "hoverinfo": 'text+name'},
                {
                    "values": [50/9, 50/9, 50/9, 50/9, 50/9, 50/9, 50/9, 50/9, 50/9, 50],
                    "rotation": 90,
                    "text": ['8-9', '7-8', '6-7', '5-6', '4-5', '3-4', '2-3', '1-2', '0-1', ''],
                    "textinfo": 'text',
                    "textposition":'inside',
                    "marker": {
                        "colors":['#add8e6','#b7dde5','#c0e1e5','#cae5e4','#d3e9e4','#dceee3','#e4f2e2','#eef7e1','#f6fae1','#ffffff']},
                        "labels": ['8-9', '7-8', '6-7', '5-6', '4-5', '3-4', '2-3', '1-2', '0-1', ''],
                        "hoverinfo": 'label',
                        "hole": .5,
                        "type": 'pie',
                        "showlegend": False
                }],
                "layout": {
                        "shapes":[{
                            "type": 'path',
                            "path": path,
                            "fillcolor": '850000',
                            "line": {
                                "color": '850000'
                            }
                            }],
                        "title": '<b>Belly Button Washing Frequency</b> <br> Scrubs per Week',
                        "height": 500,
                        "width": 500,
                        "xaxis": {"zeroline":False, "showticklabels":False,
                                    "showgrid": False, "range": [-1, 1]},
                        "yaxis": {"zeroline":False, "showticklabels":False,
                                    "showgrid": False, "range": [-1, 1]}
                    }
        	}

# bubble plot
@app.callback(Output('bubble-plot', 'figure'), [Input('name_dropdown', 'value')])
def update_bubble(name_dropdown):
    data_sample = samples(name_dropdown)

    return {
            "data": [
                {
                    "x":data_sample[0]["otu_ids"],
                    "y":data_sample[0]["sample_values"],
                    "text": data_sample[0]["otu_ids"],
                    "mode": "markers",
                    "marker": dict(
                        color = data_sample[0]["otu_ids"],
                        size = data_sample[0]["sample_values"],
                        colorscale = "YIGnBu",
                    )
                }],
            "layout": {
                	"margin": {"t": 0},
                	"hovermode": 'closest',
                	"xaxis": {"title": 'OTU ID'},
                	"width": 1147,
                	"height": 450
            	}
        }
 
if __name__ == '__main__':
    app.run_server(debug=True)