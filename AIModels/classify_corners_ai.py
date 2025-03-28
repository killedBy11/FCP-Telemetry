from keras import Sequential
from keras.src.layers import Dense
from keras.src.utils import to_categorical
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sklearn.preprocessing import StandardScaler, LabelEncoder

from DataPreprocessing.classify_corners_manually_export_gpx import load_corners
import json


def corner_to_feature_array(corner, features):
    feature_array = []
    if features[0]:
        feature_array.append(min(corner.min_radius, 0.006))
    if features[1]:
        median_radius = corner.avg_radius
        if median_radius is None:
            feature_array.append(0.006)
        else:
            feature_array.append(median_radius)
    if features[2]:
        median_radius = corner.median_radius
        if median_radius is None:
            feature_array.append(0.006)
        else:
            feature_array.append(median_radius)
    if features[4]:
        feature_array.append(corner.distance_traveled)
    if features[3]:
        feature_array.append(min(corner.max_radius, 0.006))
    return feature_array


def corners_to_feature_arrays(corners, features):
    data = []
    for corner in corners:
        feature_array = corner_to_feature_array(corner, features)
        data.append(feature_array)

    return data


def create_ann_model(input_dim, num_classes):
    model = Sequential()
    model.add(Dense(16, input_dim=input_dim, activation='relu'))
    model.add(Dense(32, activation='relu'))
    model.add(Dense(num_classes, activation='softmax'))
    model.compile(optimizer='adagrad', loss='categorical_crossentropy', metrics=['accuracy', 'recall', 'precision'])
    return model


def labels_to_numbers(labels):
    new_labels = []
    for label in labels:
        degree = None
        # get rallying notation of corners
        try:
            degree = int(label)
        except ValueError:
            if label == 'h':
                degree = -1
            if label == 'sq':
                degree = 0
            if label == 'str':
                degree = 7

        # reduce the number of categories to 3
        if -1 <= degree < 2:
            degree = 0
        elif 2 <= degree <= 4:
            degree = 1
        elif 4 < degree <= 7:
            degree = 2

        new_labels.append(degree)
    return new_labels


def get_feature_count(features):
    c = 0
    for feature in features:
        if feature:
            c += 1

    return c

def test(features, num_classes=3):
    train_corners = load_corners('./split_15_05_2024_1_2.json')
    test_corners = load_corners('../Data/CornersSplitAndLabels/split_floresti_centura_retur.json')

    train_labels = json.load(open('../Data/CornersSplitAndLabels/labels_15_05_2024_1_2.json', 'r'))
    test_labels = json.load(open('../Data/CornersSplitAndLabels/labels_floresti_centura_retur.json', 'r'))

    train_labels = labels_to_numbers(train_labels)
    test_labels = labels_to_numbers(test_labels)

    # Standardize the features
    scaler = StandardScaler()
    train_corners = scaler.fit_transform(corners_to_feature_arrays(train_corners, features))
    test_corners = scaler.transform(corners_to_feature_arrays(test_corners, features))

    # Encode the labels as one-hot vectors
    train_labels = to_categorical(train_labels, num_classes)
    test_labels = to_categorical(test_labels, num_classes)

    # Create and train the ANN model
    model = create_ann_model(get_feature_count(features), num_classes)
    model.fit(train_corners, train_labels, epochs=1200, batch_size=128, verbose=1)

    # Evaluate the model
    loss, accuracy, precision, recall = model.evaluate(test_corners, test_labels, verbose=0)
    print(features)
    print(f'ANN Model Accuracy: {accuracy:.2f}')
    print(f'ANN Model Precision: {precision:.2f}')
    print(f'ANN Model Recall: {recall:.2f}')

    # Encode the labels using LabelEncoder for Random Forest
    label_encoder = LabelEncoder()
    y_train_rf = label_encoder.fit_transform(train_labels.argmax(axis=1))
    y_test_rf = label_encoder.transform(test_labels.argmax(axis=1))

    # Define and train the Random Forest model
    rf_model = RandomForestClassifier(n_estimators=2000, random_state=42)
    rf_model.fit(train_corners, y_train_rf)

    # Predict and evaluate the model
    y_pred_rf = rf_model.predict(test_corners)
    accuracy_rf = accuracy_score(y_test_rf, y_pred_rf)
    precision_rf = precision_score(y_test_rf, y_pred_rf, average='macro')
    recall_rf = recall_score(y_test_rf, y_pred_rf, average='macro')
    print(f'Random Forest Accuracy: {accuracy_rf:.2f}')
    print(f'Random Forest Precision: {precision_rf:.2f}')
    print(f'Random Forest Recall: {recall_rf:.2f}')

    return accuracy, precision, recall, accuracy_rf, precision_rf, recall_rf


if __name__ == '__main__':
    features = [False] * 5
    features[0] = True
    features[1] = True
    features[2] = True
    features[3] = True
    features[4] = True
    test(features)
