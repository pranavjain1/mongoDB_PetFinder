from flask import Flask, request, render_template
import pymongo
import gridfs
from geopy.geocoders import Nominatim
import sys
import codecs
import re

app = Flask(__name__)

# Database Connections
client = pymongo.MongoClient("mongodb+srv://kptproject:petfinder@petfinder-en6m4.gcp.mongodb.net/test?retryWrites=true")
gridfs_db = client.petfinder_images
fs = gridfs.GridFS(gridfs_db)


def get_geo_info(state_name):
    """
    Retrieve Geographic co-ordinates based on state name
    :param state_name: Name of state
    :return: Latitude & Longitude
    """
    geo_loc = Nominatim(user_agent="krt_project")
    location = geo_loc.geocode(state_name)
    return location.latitude, location.longitude


@app.route("/")
def root():
    """
    Root directory
    :return: search.html
    """
    return render_template("search.html")


@app.route('/result_links', methods=["GET", "POST"])
def display_description():
    """
    Serve anchor links to pet documents whose description matches the query
    :return: HTML page with Links to pet documents
    """
    if request.method == 'POST':
        results = list()

        # Retrieve user's input
        query = request.form.get("query")
        location = request.form.get("location_search")
        if location is None:
            desc_exp = re.compile("\\b" + query + ".*", re.IGNORECASE)
            query_results = client["petfinder"]["pet_details"].find({"Description": desc_exp}, {"PetID": 1, "Description": 1})
            for query_result in query_results:
                results.append([query_result["PetID"], query_result["Description"]])
            return render_template("link_to_results.html", names=results)
        else:
            query_results = client["petfinder"]["pet_details"].find({"State": query}, {"PetID": 1, "Description": 1})
            for query_result in query_results:
                results.append([query_result["PetID"], query_result["Description"]])
            return render_template("link_to_results.html", names=results)

        # Find documents containing description matching user's input
        # desc_exp = re.compile("\\b" + query + ".*", re.IGNORECASE)
        # query_results = client["petfinder"]["pet_details"].find({"Description": desc_exp}, {"PetID": 1, "Description": 1})
        # for query_result in query_results:
        #     results.append([query_result["PetID"], query_result["Description"]])
        # return render_template("link_to_results.html", names=results)


@app.route('/display_doc/<string:id>')
def display_doc(id):
    """
    Parse pet ID from anchor link URL and serve HTML page with pet document
    :param id: Pet ID
    :return: HTML page with respective pet document
    """
    if request.method == 'GET':
        results = list() # Stores text info
        image_results = list()
        pet_ids = list()

        # Pet ID of pet to be displayed
        query = id

        # Retrieve all details of the pet
        query_results = client["petfinder"]["pet_details"].find({"PetID": query})

        # Parsing through results from database and adding details to results
        for query_result in query_results:
            try:
                comment = query_result["comment"]
            except:
                comment = None
            lat, long = get_geo_info(query_result["State"])
            indiv_result = [query_result["PetID"], query_result["Name"],
                        query_result["Age"], query_result["Breed1"],
                        query_result["MaturitySize"], query_result["Gender"],
                        query_result["Vaccinated"], query_result["Dewormed"],
                        query_result["Sterilized"], query_result["Fee"],
                        query_result["Description"], query_result["State"],
                        lat, long, comment]
            if query_result["PetID"] not in pet_ids:
                pet_ids.append(query_result["PetID"])
                results.append(indiv_result)

            # Retrieving images from MongoDB
            for pet_id in pet_ids:
                indiv_pet_images = list()
                reg_exp = re.compile(pet_id + "-[0-9]+\.jpg", re.IGNORECASE)
                image_file = fs.find({"file_name": reg_exp})

            for im_file in image_file:
                image_b64 = codecs.encode(im_file.read(), 'base64')
                image = image_b64.decode('utf-8')
                indiv_pet_images.append(image)
            image_results.append(indiv_pet_images)

            all_results = zip(results, image_results)
            return render_template("doc_display.html", results=all_results)


@app.route('/insertcomment/<string:pet_id>', methods=["GET", "POST"])
def insertcomment(pet_id):
    """
    Insert comment from user into database and display it
    :return: HTML page displaying updated comment
    """
    if request.method == 'POST':
        results = list() # Stores text info
        image_results = list()
        pet_ids = list()

        # Pet ID of pet to which comment is to be added
        input_params = request.form
        petid = pet_id

        # Update database with the user's comment
        query = {"PetID": petid}
        comment = input_params.get("comment")
        # print(comment, file=sys.stderr)
        print(petid, file=sys.stderr)
        client["petfinder"]["pet_details"].update(query,
                                            {"$push":{"comment": comment}})

        # Retrieve updated details
        query_results = client["petfinder"]["pet_details"].find({"PetID": petid})

        # Parsing through query output and adding them to results
        for query_result in query_results:
            lat, long = get_geo_info(query_result["State"])
            indiv_result = [query_result["PetID"], query_result["Name"],
                            query_result["Age"], query_result["Breed1"],
                            query_result["MaturitySize"], query_result["Gender"],
                            query_result["Vaccinated"], query_result["Dewormed"],
                            query_result["Sterilized"], query_result["Fee"],
                            query_result["Description"], query_result["State"],
                            lat, long, query_result["comment"]]
            if query_result["PetID"] not in pet_ids:
                pet_ids.append(query_result["PetID"])
            results.append(indiv_result)

        # Retrieving images from MongoDB
        for pet_id in pet_ids:
            indiv_pet_images = list()
            reg_exp = re.compile(pet_id + "-[0-9]+\.jpg", re.IGNORECASE)
            image_file = fs.find({"file_name": reg_exp})
            for im_file in image_file:
                image_b64 = codecs.encode(im_file.read(), 'base64')
                image = image_b64.decode('utf-8')
                indiv_pet_images.append(image)
            image_results.append(indiv_pet_images)

        all_results = zip(results, image_results)
        return render_template("doc_display.html", results=all_results)


if __name__ == "__main__":
    app.run(debug=True)
