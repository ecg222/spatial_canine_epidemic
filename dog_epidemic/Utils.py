# Define a function to recode missing values
def recode_missing(data, cols, missing):
    import pandas
    for col in cols :
        data[col].replace(missing, pandas.NA, inplace=True)

def age_at(row, birthyear, year):
    import pandas
    if pandas.isnull(row[year]) | pandas.isnull(row[birthyear]): return pandas.NA
    else: 
        if row[year] - row[birthyear] > 30:
            print("Dog older than 30 years is implausible")
            return pandas.NA
        else: 
            if row[year] - row[birthyear] < 0:
                print("Dogs cannot have negative ages")
                return pandas.NA
            else:
                return row[year] - row[birthyear]     

def pick_location(row, shape):
    import geopandas as gp
    polygon = gp.GeoSeries(row[shape])
    points = polygon.sample_points(1)
    return(points)           

def create_walk(row, location, distance = 0.015, buffer = 0.003):
    import geopandas as gp
    point = gp.GeoSeries(row[location])
    walk_radius = gp.GeoSeries(point.buffer(distance))
    walk_location = gp.GeoSeries(walk_radius.sample_points(1))
    walk_route = gp.GeoSeries(walk_location.shortest_line(point))
    walk_zone = gp.GeoSeries(walk_route.buffer(buffer))
    return(walk_zone) 

def infect_dog_along_walk(row, walk, susceptible_dogs, 
                          recovered_dogs, infected_dogs, 
                          exposed_dogs, location, 
                          max_exposed, density_factor,
                          quarantine = False, 
                          quarantine_reduction = 0.5, 
                          detected = 'detected'):
    import geopandas as gp
    import pandas as pd
    import math
    import numpy as np
    zone_of_infection = gp.GeoSeries(row['walk']).iloc[0]
    all_dogs = pd.concat([susceptible_dogs, recovered_dogs, infected_dogs, exposed_dogs])
    contacted_dogs = all_dogs[all_dogs[location].dwithin(zone_of_infection, 0, align = False) == True]
    n_contacts = len(contacted_dogs)

    if quarantine == True and row[detected] == 1:
        n_to_expose = abs(int((n_contacts ** density_factor + np.random.normal(loc = 0, scale = 1, size = 1 ))*(1-quarantine_reduction)))
    else:
        n_to_expose = abs(int(n_contacts ** density_factor + np.random.normal(loc = 0, scale = 1, size = 1 )))

    if int(n_to_expose) > max_exposed:
        n_to_expose = max_exposed

    new_infected_dogs = contacted_dogs.sample(n_to_expose)

    ## Check that dogs are not in the recovered state when exposed
    if len(recovered_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                recovered_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    ## Check that dogs are not in the infected state when exposed
    if len(infected_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                infected_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    ## Check that dogs are not in the exposed state already when exposed
    if len(exposed_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                exposed_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    return(new_infected_dogs)

def detect_infection(row, p_detection):
    import random
    pi = random.uniform(0,1)
    if pi <= p_detection:
        return 1
    else:
        return 0

def run_simulation(all_dogs, starting_zipcode, n_initially_infected = 10,
                   n_generation_intervals = 20, distance = 0.03, buffer = 0.004,
                   max_exposed_per_dog = 10, density_factor = 0.1, 
                   p_recovery = 0.1, p_detection = 0.5,
                   image_folder = 'Figures/', subtitle = ' ',
                   quarantine_on_threshold = 250, 
                   quarantine_off_threshold = 100,
                   quarantine_reduction = 0.5):
    import pandas as pd
    import geopandas as gp 
    import matplotlib.pyplot as plt
    import geoplot as gpplt
    import random
    import os
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    ## set quarnatine initially off 
    quarantine = False 
    graph_color = 'lightgray'
    edge_color = 'lightgray'

    map_bounds = gp.GeoDataFrame(all_dogs).total_bounds
    os.makedirs(image_folder, exist_ok=True)
    i = 0
    frame = 0
    SEIR_report = pd.DataFrame({'Susceptible': [], 
                                'Exposed': [], 
                                'Infected': [], 
                                'Recovered': [],
                                'Detected': [],
                                'Quarantine': []})
    R_report = pd.DataFrame()




    # Randomly infect the first generation of dogs
    exposed_dogs = all_dogs[all_dogs['ZipCode'] == starting_zipcode].sample(n_initially_infected)

    # Remove infected dogs from susceptible dogs 
    susceptible_dogs = pd.merge(all_dogs.set_index('ID'), 
                                exposed_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)

    recovered_dogs = pd.DataFrame()

    infected_dogs = pd.DataFrame()

    new_row = pd.DataFrame.from_records([{'Susceptible': len(susceptible_dogs), 
            'Exposed': len(exposed_dogs),
            'Infected': len(infected_dogs),
            'Recovered': len(recovered_dogs),
            'Detected': 0,
            'Quarantine': quarantine,
            'Step': 0}])
    SEIR_report = pd.concat([SEIR_report, new_row], ignore_index=True)

    # Run simulation for n generation intervals
    while (i < n_generation_intervals) and (exposed_dogs.shape[0] >= 1): 
        i = i + 1
        # Move dogs to next compartment
        recovered_dogs = pd.concat([recovered_dogs, infected_dogs])
        
        # Recover dogs at a specified percent chance per generation interval
        if len(recovered_dogs) > 0:
            recovered_dogs['p_end_recovery'] = [random.uniform(0,1) for k in recovered_dogs.index]
            recovering_dogs = recovered_dogs[recovered_dogs['p_end_recovery'] < p_recovery]
            recovered_dogs = pd.merge(recovered_dogs.set_index('ID'), 
                                    recovering_dogs['ID'], 
                                    on = ['ID'], how = 'outer',
                                    suffixes = ('', '_ex'),
                                    indicator=True).query('_merge=="left_only"')\
                                        .drop(['_merge', 'p_end_recovery'], axis = 1)
            susceptible_dogs = pd.concat([susceptible_dogs, recovering_dogs])
            print("Dogs recovering at generation " + str(i) + ": " + str(recovering_dogs.shape[0]))

        # Move exposed dogs to infected compartment and determine if they are detected
        infected_dogs = exposed_dogs
        infected_dogs['detected'] = infected_dogs.apply(detect_infection, axis = 1, p_detection = p_detection)
        print("Infections detected at generation " + str(i) + ": " + str(infected_dogs[infected_dogs['detected']==1].shape[0]))

        ## Create new data frame for exposed dogs
        exposed_dogs = pd.DataFrame()

        # Show infected dogs at start of step
        fig, ax = plt.subplots(1,1)
        plt.suptitle("State of the Simulation at Generation " + str(i))
        plt.title(subtitle)
        ax.set_axis_off()
        figname = os.path.join(image_folder, 'state_' + str(frame) + '.png')
        all_dogs['geometry'].plot(ax = ax, color = graph_color, edgecolor = edge_color)
        if len(recovered_dogs) > 0 :
            recovered_dogs['locations'].plot(ax = ax, 
                                        color = 'slateblue', markersize = 3.5,
                                        alpha = 0.5, edgecolor = 'none')
        infected_dogs['locations'].plot(ax = ax, 
                                        color = 'red', markersize = 3.5,
                                        alpha = 0.5, edgecolor = 'none')
        ax.set_ylim(map_bounds[1], map_bounds[3])
        ax.set_xlim(map_bounds[0], map_bounds[2])
        plt.plot([], [], label='Quarantine', alpha = 0.4, color='lightpink')
        plt.legend
        fig.savefig(figname, format= 'png')
        plt.close(fig)
        frame = frame + 1

        # Create walks for infected dogs 
        infected_dogs['walk'] = infected_dogs.apply(create_walk, axis =1, 
                                                    location = 'locations', 
                                                    distance = distance, 
                                                    buffer = buffer)

        # Show area of exposure
        fig, ax = plt.subplots(1,1)
        plt.suptitle("State of the Simulation at Generation " + str(i))
        plt.title(subtitle)
        ax.set_axis_off()
        figname = os.path.join(image_folder, 'state_' + str(frame) + '.png')
        all_dogs['geometry'].plot(ax = ax, color = graph_color, edgecolor = edge_color)
        if len(recovered_dogs) > 0 :
            recovered_dogs['locations'].plot(ax = ax, 
                                            color = 'slateblue',
                                            alpha = 0.5, markersize = 3.5,
                                            edgecolor = 'none')
        infected_dogs['walk'].plot(ax = ax, 
                                color = 'pink',
                                alpha = 0.5, 
                                edgecolor = 'none')
        infected_dogs['locations'].plot(ax = ax, 
                                        color = 'red',
                                        alpha = 0.5, markersize = 3.5,
                                        edgecolor = 'none')
        ax.set_ylim(map_bounds[1], map_bounds[3])
        ax.set_xlim(map_bounds[0], map_bounds[2])
        plt.plot([], [], label='Quarantine', alpha = 0.4, color='lightpink')
        plt.legend
        fig.savefig(figname, format= 'png')
        plt.close(fig)
        frame = frame + 1

        ## Determine if quarantine is in place
        if quarantine == False and infected_dogs[infected_dogs['detected'] == 1].shape[0] > quarantine_on_threshold:
            print('Quarantine activated: ' + str(infected_dogs[infected_dogs['detected'] == 1].shape[0]) +
                  ' detected dogs is above activation threshold of ' + str(quarantine_on_threshold))
            quarantine = True
            edge_color = 'lightpink'
        if quarantine == True and infected_dogs[infected_dogs['detected'] == 1].shape[0] < quarantine_off_threshold:
            print('Quarantine de-activated: ' + str(infected_dogs[infected_dogs['detected'] == 1].shape[0]) +
                  ' detected dogs is below de-activation threshold of ' + str(quarantine_off_threshold))
            quarantine = False
            edge_color = 'lightgray'

        # Find all dogs exposed during this step
        for index, row in infected_dogs.iterrows():
            new_exposures = infect_dog_along_walk(row,
                                walk = 'walk',
                                infected_dogs=infected_dogs, 
                                recovered_dogs=recovered_dogs, 
                                susceptible_dogs=susceptible_dogs,
                                exposed_dogs= exposed_dogs,
                                location='locations', 
                                max_exposed = max_exposed_per_dog,
                                density_factor= density_factor,
                                quarantine = quarantine, 
                                quarantine_reduction = quarantine_reduction, 
                                detected = 'detected')
            exposed_dogs= pd.concat([exposed_dogs,new_exposures])
            for index, exposed in new_exposures.iterrows():
                new_row = pd.DataFrame.from_records([{'InfectorID': row['ID'],
                                                    'Infector_ZipCode': row['ZipCode'],
                                                    'Infector_geometry': row['geometry'],
                                                    'Infector_location': row['locations'],
                                                    'ExposedID': exposed['ID'],
                                                    'Exposed_ZipCode': exposed['ZipCode'],
                                                    'Exposed_geometry': exposed['geometry'],
                                                    'Exposed_location': row['locations'],
                                                    'Count': 1,
                                                    'Step': i}])
                R_report = pd.concat([R_report, new_row], ignore_index = True)

        
        susceptible_dogs = pd.merge(susceptible_dogs.set_index('ID'), 
                                exposed_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
        # Plot newly exposed dogs 
        fig, ax = plt.subplots(1,1)
        plt.suptitle("State of the Simulation at Generation " + str(i))
        plt.title(subtitle)
        ax.set_axis_off()
        figname = os.path.join(image_folder, 'state_' + str(frame) + '.png')
        all_dogs['geometry'].plot(ax = ax, color = graph_color, edgecolor = edge_color)
        if len(recovered_dogs) > 0 :
            recovered_dogs['locations'].plot(ax = ax, color = 'slateblue', markersize = 3.5,
                                            alpha = 0.5, edgecolor = 'none')
        infected_dogs['walk'].plot(ax = ax, color = 'pink',
                                alpha = 0.5, edgecolor = 'none')
        infected_dogs['locations'].plot(ax = ax, color = 'red', markersize = 3.5,
                                        alpha = 0.5, edgecolor = 'none')
        if len(exposed_dogs) > 0:
            exposed_dogs['locations'].plot(ax = ax, color = 'black', markersize = 3.5,
                                    alpha = 0.5, edgecolor = 'none')
        ax.set_ylim(map_bounds[1], map_bounds[3])
        ax.set_xlim(map_bounds[0], map_bounds[2])
        plt.plot([], [], label='Quarantine', alpha = 0.4, color='lightpink')
        plt.legend
        fig.savefig(figname, format= 'png')
        plt.close(fig)
        frame = frame + 1

        new_row = pd.DataFrame.from_records([{'Susceptible': len(susceptible_dogs), 
            'Exposed': len(exposed_dogs),
            'Infected': len(infected_dogs),
            'Recovered': len(recovered_dogs),
            'Detected': infected_dogs[infected_dogs['detected']==1].shape[0],
            'Quarantine': quarantine,
            'Step': i}])
        SEIR_report = pd.concat([SEIR_report, new_row], ignore_index=True)

        print("Exposed dogs at generation " + str(i) + " = " + str(exposed_dogs.shape[0]))

    return((SEIR_report, R_report))