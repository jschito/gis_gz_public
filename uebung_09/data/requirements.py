import matplotlib
import matplotlib.pyplot as plt

# Use the following mode to be sure that outputs are shown in PyCharm
matplotlib.use('TkAgg')


def show_results_geopandas(df, number_of_categories, title, subtitle, legend_title, column_name, selected_classification):
    """
    Plots the results by using matplotlib
    :param df: The original DataFrame
    :param number_of_categories: The number of categories used
    :param title: The title that should be shown on the top of the map
    :param subtitle: The subtitle that should be shown on the top of the map
    :param legend_title: The legend title
    :param column_name: The name of the column that should be displayed
    :param selected_classification: The classification chosen from a predefined list
    :return:
    """

    # Set up the subplot
    fig, ax = plt.subplots(figsize=(12, 8), subplot_kw={'aspect': 'equal'})

    # Assign the new temporary column cl to the data frame and plot it
    df.plot(column=column_name,
            scheme=selected_classification,
            categorical=True,
            k=number_of_categories,
            cmap='OrRd',
            linewidth=0.1,
            ax=ax,
            edgecolor='white',
            legend=True,
            legend_kwds={'loc': 'best', 'title': legend_title, 'shadow': True},
            )

    # Set a title and a subtitle
    fig.suptitle(title, y=0.98, fontsize=16)
    plt.title(subtitle, fontsize=10)

    # Blend the axis off
    ax.set_axis_off()

    # Just for PyCharm
    #plt.show()

    # legend_kwds={'label': "Population by Country", 'orientation': "vertical"}
    return
