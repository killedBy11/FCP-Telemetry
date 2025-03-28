import json
import csv

import numpy as np
from keras import Sequential
from keras.src.layers import Dense
from keras.src.losses import mean_squared_error
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import root_mean_squared_error, mean_absolute_error
from sklearn.metrics import mean_absolute_percentage_error
from sklearn.model_selection import GridSearchCV
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt

from DataPreprocessing.classify_corners_manually_export_gpx import load_corners


def corner_to_feature_array(corner, label, features):
    feature_array = []
    if features[0]:
        feature_array.append(min(corner.min_radius, 0.01))
    if features[1]:
        r = corner.avg_radius
        if r is None:
            feature_array.append(0.01)
        else:
            feature_array.append(r)
    if features[2]:
        r = corner.median_radius
        if r is None:
            feature_array.append(0.01)
        else:
            feature_array.append(r)
    if features[3]:
        feature_array.append(min(corner.max_radius, 0.01))
    if features[4]:
        feature_array.append(corner.distance_traveled)
    if features[5]:
        feature_array.append(corner.median_speed)
    if features[6]:
        feature_array.append(corner.min_speed)
    if features[7]:
        feature_array.append(corner.max_speed)
    if features[8]:
        feature_array.append(corner.avg_speed)
    if features[9]:
        feature_array.append(corner.max_deceleration)
    if features[10]:
        feature_array.append(corner.max_acceleration)
    if features[11]:
        feature_array.append(corner.max_centrifugal)
    if features[12]:
        feature_array.append(corner.median_centrifugal)
    if features[13]:
        feature_array.append(corner.avg_centrifugal)
    if features[14]:
        feature_array.append(corner.max_rise)
    if features[15]:
        feature_array.append(corner.min_rise)
    if features[16]:
        feature_array.append(corner.avg_rise)
    if features[17]:
        feature_array.append(corner.median_rise)
    if features[18]:
        l = [0, 0, 0]
        l[label] = 1
        feature_array = feature_array + l
    if features[19]:
        feature_array.append(corner.entry_speed)
    if features[20]:
        feature_array.append(corner.exit_speed)
    if features[21]:
        feature_array.append(corner.decelerated_speed)
    if features[22]:
        feature_array.append(corner.accelerated_speed)
    if features[23]:
        feature_array.append(corner.min_map)
    if features[24]:
        feature_array.append(corner.max_map)
    if features[25]:
        feature_array.append(corner.avg_map)
    if features[26]:
        feature_array.append(corner.median_map)
    if features[27]:
        feature_array.append(corner.min_load)
    if features[28]:
        feature_array.append(corner.max_load)
    if features[29]:
        feature_array.append(corner.avg_load)
    if features[30]:
        feature_array.append(corner.median_load)
    if features[31]:
        feature_array.append(corner.entry_map)
    if features[32]:
        feature_array.append(corner.exit_map)
    if features[33]:
        feature_array.append(corner.entry_load)
    if features[34]:
        feature_array.append(corner.exit_load)

    return feature_array


def corners_to_feature_arrays(corners, labels, features):
    data = []
    for i in range(len(labels)):
        feature_array = corner_to_feature_array(corners[i], labels[i], features)
        data.append(feature_array)

    return data


# Define the ANN model
def create_ann_model(input_dim):
    model = Sequential()
    model.add(Dense(32, input_dim=input_dim, activation='relu'))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(32, activation='relu'))
    # model.add(BatchNormalization())
    model.add(Dense(16, activation='relu'))
    model.add(Dense(16, activation='relu'))
    model.add(Dense(1, activation='linear'))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def get_fuel_used(corners):
    fuel_used = []
    for corner in corners:
        fuel_used.append(corner.fuel_used)

    return fuel_used


def labels_to_numbers(labels):
    new_labels = []
    for label in labels:
        degree = None
        try:
            degree = int(label)
        except ValueError:
            if label == 'h':
                degree = -1
            if label == 'sq':
                degree = 0
            if label == 'str':
                degree = 7

        if -1 <= degree < 2:
            degree = 0
        elif 2 <= degree < 5:
            degree = 1
        else:
            degree = 2
        new_labels.append(degree)
    return new_labels


def get_feature_count(features):
    c = 0
    for feature in features:
        if feature is True:
            c += 1

    return c


def test(features, combination, test_no):
    c1 = load_corners('/Users/antoniuficard/Documents/OBDlogs/Data/CornersSplitAndLabels/split_15_05_2024_1.json')
    c2 = load_corners('/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/snap_floresti_centura_retur2.json')

    l1 = json.load(open('/Users/antoniuficard/Documents/OBDlogs/Data/CornersSplitAndLabels/labels_15_05_2024_1_2.json', 'r'))
    l2 = json.load(open('/Users/antoniuficard/Documents/OBDlogs/Data/Prezentare/labels_floresti_centura_retur.json', 'r'))

    train_input = corners_to_feature_arrays(c1, labels_to_numbers(l1), features)
    test_input = corners_to_feature_arrays(c2, labels_to_numbers(l2), features)
    train_y = np.array(get_fuel_used(c1))
    test_y = np.array(get_fuel_used(c2))

    # Standardize the features
    scaler = StandardScaler()
    train_input = scaler.fit_transform(train_input)
    test_input = scaler.transform(test_input)

    model = create_ann_model(len(train_input[0]))

    model.fit(train_input, train_y, epochs=450, batch_size=48, verbose=1)

    # Evaluate the ANN model
    y_pred_ann = model.predict(test_input).flatten()
    mape_ann = mean_absolute_percentage_error(test_y, y_pred_ann)
    mrse_ann = root_mean_squared_error(test_y, y_pred_ann)
    mse_ann = mean_squared_error(test_y, y_pred_ann)
    mae_ann = mean_absolute_error(test_y, y_pred_ann)

    # Define and train the Random Forest model

    # Define the parameter grid
    param_grid = {
        'n_estimators': [25, 50],
        'max_depth': [10, 15, 20, None],
        'min_samples_split': [2, 3, 4, 5],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2']
    }

    # Initialize the RandomForestRegressor
    rf = RandomForestRegressor(random_state=42)

    # Initialize Grid Search
    grid_search = GridSearchCV(estimator=rf, param_grid=param_grid,
                               cv=3, n_jobs=-1, verbose=2, scoring='neg_mean_squared_error')

    # Fit the model
    grid_search.fit(train_input, train_y)

    # Get the best parameters
    best_params = grid_search.best_params_
    print(f"Best parameters: {best_params}")

    # Evaluate the best model
    best_rf_model = grid_search.best_estimator_
    best_y_rf = best_rf_model.predict(test_input)

    # Evaluate the Random Forest model
    mape_rf = mean_absolute_percentage_error(test_y, best_y_rf)
    mrse_rf = root_mean_squared_error(test_y, best_y_rf)
    mse_rf = mean_squared_error(test_y, best_y_rf)
    mae_rf = mean_absolute_error(test_y, best_y_rf)
    print(features)
    sum_error_ann = abs(sum(test_y) - sum(y_pred_ann))
    rel_sum_error_ann = abs((sum(test_y) - sum(y_pred_ann)) / sum(test_y))
    sum_error_rf = abs(sum(test_y) - sum(best_y_rf))
    rel_sum_error_rf = abs((sum(test_y) - sum(best_y_rf)) / sum(test_y))
    print("ANN Model summed absolute error", sum_error_ann)
    print("ANN Model summed relative error", rel_sum_error_ann)
    print("Random Forest Model summed absolute error", sum_error_rf)
    print("Random Forest Model summed relative error", rel_sum_error_rf)

    print(f'ANN Model Mean Squared Error: {mse_ann:.2f}')
    print(f'ANN Model Mean Root Squared Error: {mrse_ann:.2f}')
    print(f'ANN Model Mean Absolute Percentage Error: {mape_ann:.2f}')
    print(f'ANN Model Mean Absolute Error: {mae_ann:.2f}')
    print(f'Random Forest Model Mean Squared Error: {mse_rf:.2f}')
    print(f'Random Forest Model Root Mean Squared Error: {mrse_rf:.2f}')
    print(f'Random Forest Model Mean Absolute Percentage Error: {mape_rf:.2f}')
    print(f'Random Forest Model Mean Absolute Error: {mae_rf:.2f}')

    plt.figure(figsize=(10, 6))

    # Plot actual results
    plt.plot(test_y, label='Actual Results', color='black', marker='o', linestyle='-')

    # Plot model 1 results
    plt.plot(y_pred_ann, label='ANN Predictions', color='blue', marker='x', linestyle='--')

    # Plot model 2 results
    plt.plot(best_y_rf, label='Random forests Predictions', color='red', marker='s', linestyle='-.')

    # Add titles and labels
    plt.title(
        'Comparison of Actual Results and Model Predictions, combination ' + str(combination + 1) + ', test ' + str(
            test_no + 1))
    plt.xlabel('Sample Index')
    plt.ylabel('Value')
    plt.legend()
    plt.grid(True)

    # Show plot
    plt.show()

    return f'{mse_ann:.2f}', f'{mrse_ann:.6f}', f'{mse_ann:.6f}', f'{mae_ann:.6f}', f'{mape_rf:.6f}', f'{mrse_rf:.6f}', f'{mse_rf:.6f}', f'{mae_rf:.6f}', f'{sum_error_ann:.6f}', f'{rel_sum_error_ann:.8f}', f'{sum_error_rf:.6f}', f'{rel_sum_error_rf:.8f}'


def display_features(features, cols):
    output = []
    for col in cols:
        output.append(features[col])
    return output


if __name__ == '__main__':
    test_features = []
    names = ['Min Radius', 'Average Radius', 'Median Radius', 'Max Radius', 'Distance traveled', 'Median Speed',
             'Min Speed', 'Max Speed', 'Average Speed', 'Min Deceleration', 'Max Acceleration', 'Max Centrifugal',
             'Median Centrifugal', 'Average Centrifugal', 'Max Rise/Run', 'Min Rise/Run', 'Average Rise/Run',
             'Median Rise/Run', 'Category', 'Entry Speed', 'Exit Speed', 'Decelerated Speed', 'Accelerated Speed',
             'Min MAP', 'Max MAP', 'Average MAP', 'Median MAP', 'Min Engine Load', 'Max Engine Load',
             'Average Engine Load', 'Median Engine Load',
             'Entry MAP', 'Exit MAP', 'Entry Engine Load', 'Exit Engine Load']

    features = [False] * 35
    features[0] = True
    features[4] = True
    features[9] = True
    features[17] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[9] = True
    features[17] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[6] = True
    features[7] = True
    features[9] = True
    features[17] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[6] = True
    features[7] = True
    features[9] = True
    features[12] = True
    features[17] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[6] = True
    features[7] = True
    features[9] = True
    features[12] = True
    features[17] = True
    features[22] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[18] = True
    features[4] = True
    features[6] = True
    features[7] = True
    features[9] = True
    features[12] = True
    features[17] = True
    features[22] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[5] = True
    features[9] = True
    features[12] = True
    features[17] = True
    features[22] = True
    features[27] = True
    features[28] = True
    features[30] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[5] = True
    features[17] = True
    features[22] = True
    test_features.append(features)

    features = [False] * 35
    features[0] = True
    features[2] = True
    features[4] = True
    features[17] = True
    test_features.append(features)

    features_cols = [0, 2, 4, 5, 9, 11, 12, 14, 17, 18, 19, 20, 21, 22, 27, 28, 30]

    csv_header = []
    for fc in features_cols:
        csv_header.append(names[fc])

    csv_header.append('MAPE ANN')
    csv_header.append('RMSE ANN')
    csv_header.append('MSE ANN')
    csv_header.append('MAE ANN')
    csv_header.append('MAPE RF')
    csv_header.append('RMSE RF')
    csv_header.append('MSE RF')
    csv_header.append('MAE RF')
    csv_header.append('Corner sum absolute error ANN')
    csv_header.append('Corner sum relative error ANN')
    csv_header.append('Corner sum absolute error RF')
    csv_header.append('Corner sum relative error RF')

    file = open('/Users/antoniuficard/Documents/OBDlogs/Data/ModelPerformance/performance2.csv', 'w')
    writer = csv.writer(file)
    writer.writerow(csv_header)

    for tf in range(len(test_features)):
        for i in range(1):
            mape_ann, mrse_ann, mse_ann, mae_ann, mape_rf, mrse_rf, mse_rf, mae_rf, sum_error_ann, rel_sum_error_ann, sum_error_rf, rel_sum_error_rf = test(
                test_features[tf], tf, i)
            of = display_features(test_features[tf], features_cols)
            row = of + [mape_ann, mrse_ann, mse_ann, mae_ann, mape_rf, mrse_rf, mse_rf, mae_rf, sum_error_ann,
                        rel_sum_error_ann,
                        sum_error_rf, rel_sum_error_rf]
            writer.writerow(row)
