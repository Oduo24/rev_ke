import React from 'react'

const Design = () => {
  return (
    <div>
        <h1>Upload a File</h1>
        <form action="/upload" method="POST" />
            <label htmlFor="file">Choose file:</label>
            <input type="file" id="file" name="file" required /><br />
            
            <label htmlFor="name">File name:</label>
            <input type="text" id="name" name="name" required /> <br />
            
            <input type="submit" value="Upload" />
    </div>
  )
}

export default Design