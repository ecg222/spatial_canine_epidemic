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
                          max_exposed, density_factor):
    import geopandas as gp
    import pandas as pd
    import math
    import numpy as np
    zone_of_infection = gp.GeoSeries(row['walk']).iloc[0]
    all_dogs = pd.concat([susceptible_dogs, recovered_dogs, infected_dogs, exposed_dogs])
    contacted_dogs = all_dogs[all_dogs[location].dwithin(zone_of_infection, 0, align = False) == True]
    n_contacts = len(contacted_dogs)

    n_to_expose = abs(int(n_contacts ** density_factor + np.random.normal(loc = 0, scale = 1, size = 1 )))

    if int(n_to_expose) > max_exposed:
        n_to_expose = max_exposed

    new_infected_dogs = contacted_dogs.sample(n_to_expose)
    if len(recovered_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                recovered_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    if len(infected_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                infected_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    if len(exposed_dogs) > 0:
        new_infected_dogs = pd.merge(new_infected_dogs.set_index('ID'), 
                                exposed_dogs['ID'], 
                                on = ['ID'], how = 'outer',
                                suffixes = ('', '_ex'),
                                indicator=True).query('_merge=="left_only"').drop('_merge', axis = 1)
    return(new_infected_dogs)